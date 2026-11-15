# Script para empaquetar el microservicio para AWS Elastic Beanstalk con compatibilidad Linux
Write-Host "Limpiando archivos temporales y cache..." -ForegroundColor Cyan
Get-ChildItem -Path . -Include __pycache__ -Recurse -Force | Remove-Item -Recurse -Force

Write-Host "Generando deploy_package_v1.zip con rutas POSIX (Linux-ready)..." -ForegroundColor Cyan
python -c "import zipfile, os; items = ['application.py', 'config.py', 'requirements.txt', 'Procfile', 'buildspec.yml', 'models', 'views', '.ebextensions']; z = zipfile.ZipFile('deploy_package_v1.zip', 'w', zipfile.ZIP_DEFLATED); [z.write(item, item) if os.path.isfile(item) else [z.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), '.').replace(os.sep, '/')) for root, _, files in os.walk(item) for f in files if '__pycache__' not in root and not f.endswith('.pyc')] for item in items]; z.close()"

Write-Host "Paquete generado exitosamente: deploy_package_v1.zip" -ForegroundColor Green

