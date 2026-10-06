<#
  Helper: fetch a URL and print only lines matching a regex, with tags stripped.
  Usage:
    .\Fetch-Snippet.ps1 -Url 'https://...' -Pattern '5131' -Max 60 -Context 1
  Keeps context small so evidence can be read without dumping whole pages.
#>
param(
  [Parameter(Mandatory = $true)][string]$Url,
  [string]$Pattern = '',
  [int]$Max = 60,
  [int]$Context = 0,
  [switch]$NoTags
)

$ErrorActionPreference = 'Stop'
try {
  $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 45
  $html = $resp.Content
  $status = $resp.StatusCode
} catch {
  Write-Output "FETCH_ERROR: $($_.Exception.Message)"
  exit 1
}

$text = $html
if (-not $NoTags) {
  $text = [regex]::Replace($text, '<script[\s\S]*?</script>', ' ')
  $text = [regex]::Replace($text, '<style[\s\S]*?</style>', ' ')
  $text = [regex]::Replace($text, '<[^>]+>', "`n")
}
$text = [System.Net.WebUtility]::HtmlDecode($text)
$lines = $text -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }

Write-Output "### URL: $Url  [HTTP $status]  lines=$($lines.Count)"
if ($Pattern -eq '') {
  $lines | Select-Object -First $Max
} else {
  $hits = $lines | Select-String -Pattern $Pattern -Context $Context, $Context
  if (-not $hits) { Write-Output "NO_MATCH for /$Pattern/" }
  else { $hits | Select-Object -First $Max | ForEach-Object { $_.ToString() } }
}