
cd ./osrm
rm -r ./data
rm -r ./turkey-latest.osm*
mkdir ./data
wget https://download.geofabrik.de/europe/turkey-latest.osm.pbf
osrm-extract -p /opt/homebrew/opt/osrm-backend/share/osrm/profiles/car.lua turkey-latest.osm.pbf
osrm-contract "turkey-latest"
