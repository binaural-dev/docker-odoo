# Restaura el acceso directo a la red interna de la oficina (10.50.x.x)
# mientras una VPN de tunel completo (ProtonVPN, etc.) esta conectada, sin
# afectar el resto del trafico (que sigue yendo por la VPN, incluido el
# acceso a Claude).
#
# Este script esta pensado para correr SOLO, en segundo plano, via la
# tarea programada que instala install-office-route-task.bat - no hace
# falta ejecutarlo a mano. Por eso no imprime nada por pantalla, solo deja
# un registro minimo en un log por si hay que revisar despues.
#
# El gateway de la red local se detecta automaticamente en cada corrida
# (cada laptop puede tener uno distinto segun su interfaz/red) - no hace
# falta editarlo a mano.

$OfficeNetwork = "10.50.0.0"
$OfficeMask    = "255.255.0.0"
$TestHost      = "10.50.27.76"
$LogPath       = Join-Path $env:TEMP "office-route.log"

function Write-Log($line) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $line" | Out-File -FilePath $LogPath -Append -Encoding utf8
}

# Get-NetIPConfiguration expone el gateway de cada adaptador via una
# propiedad (NextHop), no como texto - por eso no cambia con el idioma de
# Windows, a diferencia de parsear la salida de "ipconfig /all". Se excluye
# cualquier adaptador que parezca ser la VPN (TAP/WireGuard/Proton/Virtual)
# para no terminar usando el gateway de la propia VPN.
$adapter = Get-NetIPConfiguration | Where-Object {
    $_.IPv4DefaultGateway -and
    $_.NetAdapter.Status -eq "Up" -and
    $_.InterfaceDescription -notmatch "VPN|TAP|WireGuard|Proton|Virtual|Tunnel"
} | Select-Object -First 1

if (-not $adapter) {
    Write-Log "no se pudo detectar el gateway de la red local (ningun adaptador fisico activo con gateway) - ruta NO agregada"
    exit 1
}

$OfficeGateway = $adapter.IPv4DefaultGateway.NextHop

# "route add" falla con "El objeto ya existe" si la ruta ya esta puesta -
# no es un error real, simplemente significa que no hacia falta agregarla.
route add $OfficeNetwork mask $OfficeMask $OfficeGateway | Out-Null

$reachable = Test-Connection -ComputerName $TestHost -Count 1 -Quiet -ErrorAction SilentlyContinue
Write-Log "gateway detectado: $OfficeGateway ($($adapter.InterfaceAlias)) - red interna ($TestHost) alcanzable: $reachable"
