param([string]$OutputFolder)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$taskRoot = Split-Path $PSScriptRoot -Parent
$fontOutput = Join-Path $OutputFolder 'loading_font.h'
$fontCollection = New-Object System.Text.StringBuilder
[void]$fontCollection.AppendLine('#pragma once')
$fontFormat = [System.Drawing.StringFormat]::GenericTypographic.Clone()
$fontFormat.FormatFlags = $fontFormat.FormatFlags -bor [System.Drawing.StringFormatFlags]::MeasureTrailingSpaces
$privateFonts = New-Object System.Drawing.Text.PrivateFontCollection
$privateFonts.AddFontFile((Join-Path $taskRoot 'tools/branding/fonts/NotoSans-Bold.ttf'))
$bodyFont = New-Object System.Drawing.Font($privateFonts.Families[0],16,[System.Drawing.FontStyle]::Bold,[System.Drawing.GraphicsUnit]::Pixel)
$glyphCanvas = New-Object System.Drawing.Bitmap(24,24)
$glyphGraphics = [System.Drawing.Graphics]::FromImage($glyphCanvas)
$glyphGraphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$glyphBytes = New-Object 'System.Collections.Generic.List[byte]'
$glyphWidths = New-Object 'System.Collections.Generic.List[byte]'
for ($glyphCode=32; $glyphCode -lt 127; $glyphCode++) {
    $glyphText = [string][char]$glyphCode
    $glyphGraphics.Clear([System.Drawing.Color]::Transparent)
    $glyphGraphics.DrawString($glyphText,$bodyFont,[System.Drawing.Brushes]::White,0,0,$fontFormat)
    $glyphWidths.Add([byte][Math]::Ceiling($glyphGraphics.MeasureString($glyphText,$bodyFont,1000,$fontFormat).Width))
    for ($glyphY=0; $glyphY -lt 24; $glyphY++) {
        for ($glyphX=0; $glyphX -lt 24; $glyphX++) { $glyphBytes.Add($glyphCanvas.GetPixel($glyphX,$glyphY).A) }
    }
}
[void]$fontCollection.AppendLine(('static const unsigned char loading_glyphs[]={' + [string]::Join(',',$glyphBytes) + '};'))
[void]$fontCollection.AppendLine(('static const unsigned char loading_widths[]={' + [string]::Join(',',$glyphWidths) + '};'))
$brandFont = New-Object System.Drawing.Font($privateFonts.Families[0],28,[System.Drawing.FontStyle]::Bold,[System.Drawing.GraphicsUnit]::Pixel)
$brandWidth = [int][Math]::Ceiling($glyphGraphics.MeasureString('PictoPlus',$brandFont,1000,$fontFormat).Width)
$brandCanvas = New-Object System.Drawing.Bitmap($brandWidth,42)
$brandGraphics = [System.Drawing.Graphics]::FromImage($brandCanvas)
$brandGraphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$brandGraphics.DrawString('PictoPlus',$brandFont,[System.Drawing.Brushes]::White,0,0,$fontFormat)
$brandBytes = New-Object 'System.Collections.Generic.List[byte]'
for ($brandY=0; $brandY -lt 42; $brandY++) {
    for ($brandX=0; $brandX -lt $brandWidth; $brandX++) { $brandBytes.Add($brandCanvas.GetPixel($brandX,$brandY).A) }
}
[void]$fontCollection.AppendLine("#define LOADING_BRAND_WIDTH $brandWidth")
[void]$fontCollection.AppendLine(('static const unsigned char loading_brand[]={' + [string]::Join(',',$brandBytes) + '};'))
[System.IO.File]::WriteAllText($fontOutput,$fontCollection.ToString(),[System.Text.Encoding]::ASCII)
$glyphGraphics.Dispose(); $glyphCanvas.Dispose(); $bodyFont.Dispose()
$brandGraphics.Dispose(); $brandCanvas.Dispose(); $brandFont.Dispose(); $fontFormat.Dispose(); $privateFonts.Dispose()
Write-Output "Prepared loading-screen lettering: $fontOutput"

$source=[System.Drawing.Bitmap]::new((Join-Path $taskRoot 'app/assets/pictoplus-logo.png'))
$canvas=[System.Drawing.Bitmap]::new(90,90)
$g=[System.Drawing.Graphics]::FromImage($canvas)
$g.Clear([System.Drawing.Color]::Transparent)
$g.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$g.DrawImage($source,0,0,90,90)
$bytes=[System.Collections.Generic.List[byte]]::new()
for($y=0;$y -lt 90;$y++){for($x=0;$x -lt 90;$x++){$c=$canvas.GetPixel($x,$y);$bytes.Add($c.R);$bytes.Add($c.G);$bytes.Add($c.B);$bytes.Add($c.A)}}
[System.IO.File]::WriteAllText((Join-Path $OutputFolder 'loading_logo.h'),('#pragma once'+"`n"+'static const unsigned char loading_logo[]={'+[string]::Join(',',$bytes)+'};'),[System.Text.Encoding]::ASCII)
$g.Dispose();$source.Dispose();$canvas.Dispose()
