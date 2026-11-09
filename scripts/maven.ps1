$ErrorActionPreference='Stop'
$repoRoot=Split-Path -Parent $PSScriptRoot
if(!$env:JAVA_HOME){
 $javaCommand=Get-Command java -ErrorAction SilentlyContinue
 if($javaCommand){$env:JAVA_HOME=Split-Path -Parent (Split-Path -Parent $javaCommand.Source)}
 else {$jdk=Get-ChildItem -LiteralPath "$env:ProgramFiles\Amazon Corretto" -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1; if($jdk){$env:JAVA_HOME=$jdk.FullName}}
}
if(!$env:JAVA_HOME -or !(Test-Path -LiteralPath "$env:JAVA_HOME\bin\java.exe")){throw 'Install Java 21 and set JAVA_HOME.'}
$env:PATH="$env:JAVA_HOME\bin;$env:PATH"
$mavenCommand=Get-Command mvn.cmd -ErrorAction SilentlyContinue
$mavenPath=if($mavenCommand){$mavenCommand.Source}elseif($env:MAVEN_HOME){Join-Path $env:MAVEN_HOME 'bin\mvn.cmd'}else{$null}
if(!$mavenPath){foreach($idea in (Get-ChildItem -LiteralPath "$env:ProgramFiles\JetBrains" -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending)){$candidate=Join-Path $idea.FullName 'plugins\maven\lib\maven3\bin\mvn.cmd';if(Test-Path -LiteralPath $candidate){$mavenPath=$candidate;break}}}
if(!$mavenPath){throw 'Install Maven and add mvn.cmd to PATH, or set MAVEN_HOME.'}
$mavenArguments=@(if($args.Count){$args}else{'verify'})
Push-Location $repoRoot
try {& $mavenPath @mavenArguments;exit $LASTEXITCODE} finally {Pop-Location}
