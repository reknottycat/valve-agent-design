"""Minimal evidence-claim checker. No engineering acceptance is inferred."""
import json
import sys


def validate(record):
    errors = []
    required = ('artifact_id', 'source', 'scope', 'verification', 'claim', 'input_refs', 'tool_version')
    for key in required:
        if key not in record:
            errors.append('missing:' + key)
    if errors:
        return errors
    if record['verification'] not in ('listed', 'text_read', 'bytes_verified', 'reproduced'):
        errors.append('unknown_verification_level')
    if record['claim'] == 'byte_identity' and record['verification'] not in ('bytes_verified', 'reproduced'):
        errors.append('text_or_listing_is_not_byte_verification')
    if record.get('claim_scope', record['scope']) != record['scope']:
        errors.append('scope_mismatch_requires_separate_evidence')
    if record.get('gate_status') == 'pass':
        if not record.get('gate_source') or not record.get('observations'):
            errors.append('pass_requires_criterion_and_observation')
        if record.get('unknowns_required_for_gate'):
            errors.append('unknown_required_gate_inputs')
    if record.get('claim') == 'manufacturing_release':
        errors.append('manufacturing_release_not_supported_by_this_checker')
    return errors


if __name__ == '__main__':
    record = json.load(open(sys.argv[1], encoding='utf-8'))
    errors = validate(record)
    print(json.dumps({'contract_valid': not errors, 'errors': errors,
                      'engineering_acceptance_inferred': False}, ensure_ascii=False))
    sys.exit(bool(errors))
