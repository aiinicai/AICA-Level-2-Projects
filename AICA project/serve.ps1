param([int]$Port = 8971, [string]$Root = $PSScriptRoot)
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$Port/")
$listener.Start()
Write-Output "serving $Root"
Write-Output "open http://localhost:$Port/ in Chrome or Edge (Ctrl+C or close this window to stop)"
$types = @{ ".html"="text/html; charset=utf-8"; ".js"="application/javascript"; ".css"="text/css"; ".json"="application/json"; ".pdf"="application/pdf"; ".xlsx"="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"; ".txt"="text/plain; charset=utf-8" }
while ($listener.IsListening) {
  try {
    $ctx = $listener.GetContext()
    $rel = [Uri]::UnescapeDataString($ctx.Request.Url.AbsolutePath).TrimStart('/')
    if ($rel -eq "") { $rel = "GST Tool.html" }
    if ($rel -eq "__quit") { $ctx.Response.StatusCode = 200; $ctx.Response.Close(); break }
    $file = Join-Path $Root $rel
    if (Test-Path $file -PathType Leaf) {
      $ext = [IO.Path]::GetExtension($file).ToLower()
      $ct = $types[$ext]; if (-not $ct) { $ct = "application/octet-stream" }
      $bytes = [IO.File]::ReadAllBytes($file)
      $ctx.Response.ContentType = $ct
      $ctx.Response.Headers.Add("Access-Control-Allow-Origin","*")
      $ctx.Response.ContentLength64 = $bytes.Length
      $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
    } else {
      $ctx.Response.StatusCode = 404
      $msg = [Text.Encoding]::UTF8.GetBytes("not found: $rel")
      $ctx.Response.OutputStream.Write($msg, 0, $msg.Length)
    }
    $ctx.Response.Close()
  } catch { }
}
$listener.Stop()
