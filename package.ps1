# Script para empaquetar el microservicio para AWS Elastic Beanstalk
Write-Host "Limpiando archivos temporales y cache..." -ForegroundColor Cyan
Get-ChildItem -Path . -Include __pycache__ -Recurse -Force | Remove-Item -Recurse -Force

Write-Host "Generando deploy_package_v1.zip..." -ForegroundColor Cyan
Compress-Archive -Path application.py, config.py, requirements.txt, models, views, .ebextensions -DestinationPath deploy_package_v1.zip -Force

Write-Host "Paquete generado exitosamente: deploy_package_v1.zip" -ForegroundColor Green
