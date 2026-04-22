[#]
# Meeting Cost Tracker - PowerShell Skill Wrapper
# Usage: .\invoke.ps1 [arguments...]
#

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonModule = "meeting_cost_tracker.cli"

# Check if we're in a virtual environment
if ($env:VIRTUAL_ENV) {
    $pythonCmd = "python"
} else {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
    }
    if (-not $pythonCmd) {
        Write-Error "Python not found. Please install Python 3.10 or later."
        exit 1
    }
    $pythonCmd = $pythonCmd.Source
}

# Check if package is installed, if not use local source
$moduleCheck = & $pythonCmd -c "import meeting_cost_tracker" 2>&1
if ($LASTEXITCODE -ne 0) {
    # Use local source
    $srcDir = Join-Path $scriptDir "src"
    $env:PYTHONPATH = "$srcDir;$env:PYTHONPATH"
}

# Run the CLI
& $pythonCmd -m $pythonModule @Arguments
