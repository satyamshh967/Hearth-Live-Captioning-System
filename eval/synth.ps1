param (
    [string]$Text,
    [string]$OutputFile
)

Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SetOutputToWaveFile($OutputFile)
$synth.Speak($Text)
$synth.Dispose()
Write-Output "Generated: $OutputFile"
