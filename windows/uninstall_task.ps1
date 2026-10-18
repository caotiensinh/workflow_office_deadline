& schtasks.exe /Delete /F /TN EducationAIWorkflow
if ($LASTEXITCODE -ne 0) { throw 'Task removal failed. Check permissions/Task Scheduler status.' }
