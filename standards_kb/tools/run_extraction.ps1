$ErrorActionPreference = 'Continue'
$py = 'python'
# 用 $PSScriptRoot 而不是硬编码中文绝对路径:
# 硬编码路径在 GBK 保存的 .ps1 里会变成乱码,Set-Location 失败后脚本仍继续跑,
# 造成「抽取成功但其实工作目录是错的」的假象。
$tools = $PSScriptRoot
if (-not $tools) { $tools = Split-Path -Parent $MyInvocation.MyCommand.Path }
Set-Location $tools

Write-Output '========== 文本层抽取 =========='
$textJobs = @(
  @{ s='ASME-B31.1';    f='..\runs\ASME-B31.1\asme_b31_1_2007_djvu.txt' },
  @{ s='ASME-B31.4';    f='..\runs\ASME-B31.4\asme_b31_4_2002_djvu.txt' },
  @{ s='ASME-BPVC-IV';  f='..\runs\ASME-BPVC-IV\asme_bpvc_iv_2007_djvu.txt' },
  @{ s='ASME-BPVC-VII'; f='..\runs\ASME-BPVC-VII\asme_bpvc_vii_2010_djvu.txt' },
  @{ s='ASME-BPVC-IX';  f='..\runs\ASME-BPVC-IX\asme_bpvc_ix_2010_djvu.txt' }
)
foreach ($j in $textJobs) {
  Write-Output ("-- " + $j.s)
  & $py extract.py --source $j.s --file $j.f --no-pdf 2>&1 | Select-Object -Last 4
}

Write-Output '========== PDF 版面抽取 =========='
$pdfJobs = @(
  @{ s='ASME-B31.4';    p='..\runs\ASME-B31.4\asme_b31_4_2002.pdf' },
  @{ s='ASME-B31.9';    p='..\runs\ASME-B31.9\asme_b31_9_2008.pdf' },
  @{ s='ASME-BPVC-VII'; p='..\runs\ASME-BPVC-VII\asme_bpvc_vii_2010.pdf' }
)
foreach ($j in $pdfJobs) {
  Write-Output ("-- " + $j.s)
  & $py extract_pdf.py --source $j.s --pdf $j.p 2>&1 | Select-Object -Last 4
}
Write-Output '========== 完成 =========='
