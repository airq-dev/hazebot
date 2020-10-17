mapboxgl.accessToken = 'pk.eyJ1IjoiZTNrbHVuZCIsImEiOiJja2c1bDJ5ZW8wYnp4MnNuenRwc3diZ2w4In0.7pXGkCpKkhFHDm3TMwjgAg';
var map = new mapboxgl.Map({
    container: 'map',
    style: 'mapbox://styles/mapbox/streets-v11',
    center: [-122.25948, 37.87221],
    zoom: 10
});

map.addControl(
    new MapboxGeocoder({
        accessToken: mapboxgl.accessToken,
        render: function (item) {
            return (
                "<div class='geocoder-dropdown-item'>" + "<span class='geocoder-dropdown-text'>" + item.place_name + '</span></div>'
            );
        },
        mapboxgl: mapboxgl,
        placeholder: 'Enter a zipcode'
    })
);

// After the map style has loaded on the page,
// add a source layer and default styling for a single point
map.on('load', function() {
    map.addSource('single-point', {
        type: 'geojson',
        data: {
        type: 'FeatureCollection',
        features: []
        }
    });

    map.addLayer({
        id: 'point',
        source: 'single-point',
        type: 'circle',
        paint: {
        'circle-radius': 9,
        'circle-color': '#448ee4'
        }
    });

});
// const sensors = {{points|tojson}};
// console.log(sensors);

// static lat/long for the markers in development
var geojson = {
    type: 'FeatureCollection',
    features: [{
        type: 'Feature',
        geometry: {
            type: 'Point',
            coordinates: [-77.032, 38.913]
        },
    },
    {
        type: 'Feature',
        geometry: {
            type: 'Point',
            coordinates: [-122.414, 37.776]
        },
    }]
};

// add markers to map
geojson.features.forEach(function(marker) {

    // create a HTML element for each feature
    var el = document.createElement('div');
    el.className = 'marker';

    // make a marker for each feature and add to the map
    new mapboxgl.Marker(el)
    .setLngLat(marker.geometry.coordinates)
    .addTo(map);
});
