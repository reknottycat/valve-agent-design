// Verification only: native geometry probe + manufactured Poisson equation.
// Target: OpenCFD/ESI OpenFOAM v1912, serial, double precision.
// This is NOT a physical valve-flow, contact, joint or release calculation.
#include "fvCFD.H"
#include <fstream>
#include <iomanip>
#include <cmath>

int main(int argc, char *argv[])
{
    argList::addBoolOption("probeOnly", "Write native C, Cf, Sf and V only");
    #include "setRootCase.H"
    #include "createTime.H"
    #include "createMesh.H"

    if (Pstream::parRun())
    {
        FatalErrorInFunction << "Serial-only evidence utility" << exit(FatalError);
    }
    const volVectorField& C = mesh.C();
    const surfaceVectorField& Cf = mesh.Cf();
    const surfaceVectorField& Sf = mesh.Sf();
    std::ofstream cells((runTime.path()/"native_cells.csv").c_str());
    std::ofstream faces((runTime.path()/"native_faces.csv").c_str());
    cells << std::setprecision(17) << "id,x,y,z,volume\n";
    faces << std::setprecision(17) << "id,x,y,z,sx,sy,sz,patch\n";
    forAll(C, i)
    {
        cells << i << ',' << C[i].x() << ',' << C[i].y() << ','
              << C[i].z() << ',' << mesh.V()[i] << '\n';
    }
    forAll(Cf.primitiveField(), i)
    {
        const vector& c = Cf[i];
        const vector& s = Sf[i];
        faces << i << ',' << c.x() << ',' << c.y() << ',' << c.z()
              << ',' << s.x() << ',' << s.y() << ',' << s.z() << ",-1\n";
    }
    forAll(mesh.boundary(), patchi)
    {
        const label start = mesh.boundary()[patchi].start();
        forAll(Cf.boundaryField()[patchi], j)
        {
            const vector& c = Cf.boundaryField()[patchi][j];
            const vector& s = Sf.boundaryField()[patchi][j];
            faces << start+j << ',' << c.x() << ',' << c.y() << ',' << c.z()
                  << ',' << s.x() << ',' << s.y() << ',' << s.z()
                  << ',' << patchi << '\n';
        }
    }
    cells.close();
    faces.close();
    if (!cells || !faces)
    {
        FatalErrorInFunction << "Cannot save geometry evidence" << exit(FatalError);
    }
    if (args.optionFound("probeOnly"))
    {
        Info << "NATIVE_GEOMETRY_WRITTEN" << endl;
        return 0;
    }

    volScalarField T
    (
        IOobject("T", runTime.timeName(), mesh, IOobject::MUST_READ, IOobject::AUTO_WRITE),
        mesh
    );
    // Boundary values come from native Cf, never the independent Python probe.
    forAll(T.boundaryField(), patchi)
    {
        if (T.boundaryField()[patchi].type() != "fixedValue")
        {
            FatalErrorInFunction << "All MMS patches must be fixedValue" << exit(FatalError);
        }
        T.boundaryFieldRef()[patchi] == magSqr(Cf.boundaryField()[patchi]);
    }
    T.correctBoundaryConditions();
    scalar exactScale = 0;
    forAll(C, i) exactScale = max(exactScale, magSqr(C[i]));
    if (exactScale <= VSMALL)
    {
        FatalErrorInFunction << "Invalid manufactured field scale" << exit(FatalError);
    }
    std::ofstream history((runTime.path()/"iterations.csv").c_str());
    history << std::setprecision(17)
            << "iteration,initial_residual,final_residual,linear_iterations,max_scaled_update\n";
    bool converged = false;
    for (label iteration=1; iteration<=4000; ++iteration)
    {
        const scalarField previous(T.primitiveField());
        // T [m^2], Laplacian(T) [1]. Positive diagonal form: -Lap(T) = -6.
        // Every rebuild recomputes the explicit non-orthogonal correction.
        fvScalarMatrix equation
        (
            -fvm::laplacian(T) == dimensionedScalar("minusSix", dimless, -6.0)
        );
        const auto performance = equation.solve();
        scalar maxUpdate = 0;
        forAll(T, i)
        {
            if (!std::isfinite(T[i]))
            {
                FatalErrorInFunction << "Non-finite T" << exit(FatalError);
            }
            maxUpdate = max(maxUpdate, mag(T[i]-previous[i])/exactScale);
        }
        history << iteration << ',' << performance.initialResidual() << ','
                << performance.finalResidual() << ',' << performance.nIterations()
                << ',' << maxUpdate << '\n';
        // Require updated-matrix residual AND small correction; inner solve alone is insufficient.
        if (iteration >= 3 && performance.initialResidual() <= 1e-8
            && performance.finalResidual() <= 1e-10 && maxUpdate <= 1e-10)
        {
            converged = true;
            break;
        }
    }
    history.close();
    runTime.setTime(scalar(1), 1);
    T.write();
    std::ofstream field((runTime.path()/"manufactured_field.csv").c_str());
    field << std::setprecision(17) << "id,T,T_exact,error\n";
    forAll(T, i)
    {
        const scalar exact = magSqr(C[i]);
        field << i << ',' << T[i] << ',' << exact << ',' << T[i]-exact << '\n';
    }
    field.close();
    if (!history || !field)
    {
        FatalErrorInFunction << "Cannot save solver evidence" << exit(FatalError);
    }
    if (!converged)
    {
        Info << "MMS_NOT_CONVERGED" << endl;
        return 3;
    }
    Info << "MMS_CONVERGED" << endl;
    return 0;
}
