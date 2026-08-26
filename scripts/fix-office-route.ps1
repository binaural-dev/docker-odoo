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
# Si el gateway de la oficina cambia, o esto se usa desde otra red, ajustar
# $OfficeGateway aqui abajo (confirmar antes con: route print).

$OfficeNetwork = "10.50.0.0"
$OfficeMask    = "255.255.0.0"
$OfficeGateway = "10.50.154.1"
$TestHost      = "10.50.27.76"
$LogPath       = Join-Path $env:TEMP "office-route.log"

# "route add" falla con "El objeto ya existe" si la ruta ya esta puesta -
# no es un error real, simplemente significa que no hacia falta agregarla.
route add $OfficeNetwork mask $OfficeMask $OfficeGateway | Out-Null

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$reachable = Test-Connection -ComputerName $TestHost -Count 1 -Quiet -ErrorAction SilentlyContinue
"$timestamp - red interna ($TestHost) alcanzable: $reachable" | Out-File -FilePath $LogPath -Append -Encoding utf8
