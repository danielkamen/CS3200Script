import os
import json
import csv
import rasterio

HGT_FOLDER = './K18/'


def find_tile(lat, lon):
    ns = 'N' if lat >= 0 else 'S'
    ew = 'E' if lon >= 0 else 'W'
    return f"{ns}{abs(int(lat)):02d}{ew}{abs(int(lon)):03d}"


def load_tile(lat, lon):
    tile_name = find_tile(lat, lon)
    file_path = os.path.join(HGT_FOLDER, f"{tile_name}.hgt")
    if not os.path.exists(file_path):
        print(f"Tile not found: {tile_name}.hgt")
        return None
    return rasterio.open(file_path)


def get_elevation(lat, lon):
    tile = load_tile(lat, lon)
    if not tile:
        return None
    try:
        row, col = tile.index(lon, lat)
        elevation = tile.read(1)[col, row]
        if elevation == tile.nodata:
            return None
        return float(elevation)
    except Exception as e:
        print(f"Error reading elevation at {lat}, {lon}: {e}")
        return None


def get_elevation_stats(coords):
    elevations = []
    for lat, lon in coords:
        elev = get_elevation(lat, lon)
        if elev is not None:
            elevations.append(elev)

    if len(elevations) < 2:
        return None, None

    max_elev = max(elevations)
    elevation_gain = sum(
        elevations[i] - elevations[i - 1]
        for i in range(1, len(elevations))
        if elevations[i] > elevations[i - 1]
    )
    # convert to feet
    return round(max_elev * 3.28084, 2), round(elevation_gain * 3.28084, 2)


def parse_geojsonl(file_path):
    trails = []
    with open(file_path, 'r') as f:
        for line in f:
            feature = json.loads(line.strip())
            props = feature['properties']
            name = props.get('name')
            if not name:
                continue
            geom = feature['geometry']
            coords = geom.get('coordinates', [[]])[0]
            coordinates = [(lat, lon) for lon, lat in coords]
            if not coordinates:
                continue
            start_coords = coordinates[0]
            end_coords = coordinates[-1]
            max_elev, elevation_gain = get_elevation_stats(coordinates)

            trail = {
                'name': name,
                'state': 'CT',
                'start_coordinates': f"{start_coords[0]}, {start_coords[1]}",
                'end_coordinates': f"{end_coords[0]}, {end_coords[1]}",
                'length': props.get('lengthmiles', 0.0),
                'elevation_gain': elevation_gain,
                'difficulty_rating': None,
                'max_altitude': max_elev,
                'dogs_allowed': 1 if props.get('hikerpedestrian', 'N') == 'Y' else 0
            }

            trails.append(trail)

    return trails


def write_to_csv(trails, output_path):
    keys = ['name', 'state', 'start_coordinates', 'end_coordinates',
            'length', 'elevation_gain', 'difficulty_rating', 'max_altitude', 'dogs_allowed']

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(trails)


if __name__ == '__main__':
    input_path = './smallSubSetOfGeodata.geojsonl'
    output_path = './trails_with_elevation.csv'

    print("Parsing trails and calculating elevation")
    trails = parse_geojsonl(input_path)

    print("Writing to CSV")
    write_to_csv(trails, output_path)

    print(f"Parsed {len(trails)} trails with elevation data")
