mapboxgl.accessToken = 'pk.eyJ1IjoiamdmOTQiLCJhIjoiY2thaXk2bjQzMDZvYzJ3cXoxeThnODU5NyJ9.o1ijddB0igPdlsWMw6iRVw';
const { MapboxLayer, PointCloudLayer } = deck;
		
var map = new mapboxgl.Map({
	container: 'map',
	style: 'mapbox://styles/jgf94/ckg7ai9oo06zj19p6zw741oe2', 
	center: [ -73.993, 40.707 ],
	zoom: 10,
	pitch: 60,
	bearing: 0,
	antialias: true
	});

map.on('load', function() {
	
	map.addSource('trees', { type: 'geojson', 
		cluster: true,
		clusterMaxZoom: 15,
		clusterRadius: 50,
		data: './data/geojson/tree_census_geojson.geojson'
		});


  	map.addLayer(
		{
		'id': '3d-buildings',
		'source': 'composite',
		'source-layer': 'building',
		'filter': ['==', 'extrude', 'true'],
		'layout':{'visibility':'visible'},
		'type': 'fill-extrusion',
		'minzoom': 15,
		'paint': {
			'fill-extrusion-color': 'rgb(200,200,200)',
			 
			// use an 'interpolate' expression to add a smooth transition effect to the
			// buildings as the user zooms in
			'fill-extrusion-height': [
			'interpolate',
			['linear'],
			['zoom'],
			15,
			0,
			15.05,
			['get', 'height']
			],
			'fill-extrusion-base': [
			'interpolate',
			['linear'],
			['zoom'],
			15,
			0,
			15.05,
			['get', 'min_height']
			],
			'fill-extrusion-opacity': 0.4
			}
			}
		);

	map.addLayer(
		{
		'id': 'clusters',
		'type': 'circle',
		'source': 'trees',
		'filter': ['has', 'point_count'],
		'paint': {
		// Use step expressions (https://docs.mapbox.com/mapbox-gl-js/style-spec/#expressions-step)
		// with three steps to implement three types of circles:
		//   * Blue, 20px circles when point count is less than 100
		//   * Yellow, 30px circles when point count is between 100 and 750
		//   * Pink, 40px circles when point count is greater than or equal to 750
		'circle-pitch-alignment':'map',
		'circle-color':'rgba(255,255,255,0)',
		'circle-stroke-color': [
			'interpolate',
			['linear'],
			['get', 'point_count'],
			50,
			'rgba(75,100,75,0.6)',
			500,
			'rgba(50,150,50,0.7)',
			2000,
			'rgba(0,200,0,0.8)'
			],
		'circle-radius': [
			'interpolate',
			['linear'],
			['get', 'point_count'],
			0,
			5,
			100,
			10,
			2000,
			20
			],
		'circle-stroke-width':{
			'base': 1,
			'stops': [
				[10, 2],
				[16, 4],
				[22, 8]
				]}
		}
		});

	map.addLayer({
		'id': 'trees1',
		'type': 'circle',
		'source': 'trees',
		'filter': ['!', ['has', 'point_count']],
		'layout':{'visibility':'visible'},
		'paint': {
			// make circles larger as the user zooms from z12 to z22
			'circle-radius': [
		    "interpolate",
		    ["exponential", 2],
		    ["zoom"],
		    0,1,
		    //5,['/',['get', 'tree_dbh'],20],
		    //15, ['*',0.01,['^',['/',['get', 'tree_dbh'],2],1]],
		    22, ['*',10,['get', 'tree_dbh']],
			],

			'circle-pitch-alignment':'map',
			'circle-color':'rgba(255,255,255,0)',
			'circle-stroke-color': [
			'interpolate',
			['linear'],
			['get', 'tree_dbh'],
			6,
			'rgba(150,150,50,0.6)',
			36,
			'rgba(50,200,75,0.8)'
			],
			'circle-stroke-width':{
			'base': 1,
			'stops': [
				[10, 0.75],
				[16, 1.5],
				[22, 5]
				]}
			//'circle-opacity':0.3
			}
		});



	map.on('mouseenter', 'trees1', function(e) {
		map.getCanvas().style.cursor = 'pointer';
		});
	// Change it back to a pointer when it leaves.
	map.on('mouseleave', 'trees1', function() {
		map.getCanvas().style.cursor = '';
		});

	var treeID;
	var treeLat;
	var treeLon;

	function shadow(treeID,treeLat,treeLon,az,amp,darkness,name,bool) {

		var pointCloudFile = 'data/csv_out_deck/';
		var pointCloudFile = pointCloudFile.concat(treeID);
		var pointCloudFile = pointCloudFile.concat('.json');
		var shadow = 'shadow'.concat(treeID);

		var az = parseInt(az);
		var amp = parseInt(amp);

		var sinAz = Math.sin((az) * Math.PI / 180);
		var cosAz = Math.cos((az) * Math.PI / 180);
		var tanAz = Math.tan((az) * Math.PI / 180);
		var sinAmp = Math.sin((amp-90) * Math.PI / 180);
		var cosAmp = Math.cos((amp-90) * Math.PI / 180);
		var tanAmp = Math.tan((-amp) * Math.PI / 180);

		var name = 'shadow'.concat(name);

		map.addLayer(new MapboxLayer({
	    	id: name,
	    	type: PointCloudLayer,
	    	data: pointCloudFile,
	    	coordinateSystem: COORDINATE_SYSTEM.METER_OFFSETS,
    		coordinateOrigin: [treeLat, treeLon],
	    	getPosition: d => [ d[0]/3.28 + (d[2]/tanAmp*(sinAz)), d[1]/3.28 + (d[2]/tanAmp*(cosAz)), 0.1 ], //for Z position d[2]*0
	    	getColor: d => [ 255-100*(darkness*darkness)*(d[5]-d[4]), 255-100*(darkness*darkness)*(d[5]-d[4]), 255-100*(darkness*darkness)*(d[5]-d[4]), 150*(darkness*darkness)*(d[5]-d[4]) ],
	    	sizeUnits: 'feet',
	    	pointSize: 2,
	    	//opacity: darkness*3,
	    	visible: bool
	    	}));

		};

	map.on('click', 'trees1', function(e) {

		map.removeLayer('tree');

		map.removeLayer('shadow1');
		map.removeLayer('shadow2');
		map.removeLayer('shadow3');
		map.removeLayer('shadow4');
		map.removeLayer('shadow5');
		map.removeLayer('shadow6');
		map.removeLayer('shadow7');
		map.removeLayer('shadow8');
		map.removeLayer('shadow9');
		map.removeLayer('shadow10');
		map.removeLayer('shadow11');
		map.removeLayer('shadow12');
		map.removeLayer('shadow13');
		map.removeLayer('shadow14');
		map.removeLayer('shadow15');

		treeID = e.features[0].properties['tree_id'];
		treeLat = e.features[0].properties['the_geom'];
		treeLat = treeLat.split(' ')[1];
		treeLat = treeLat.split('(')[1];
		treeLat = parseFloat(treeLat);
		//console.log(treeLat);
		
		treeLon = e.features[0].properties['the_geom'];
		treeLon = treeLon.split(' ')[2];
		treeLon = treeLon.split(')')[0];
		treeLon = parseFloat(treeLon);
		//console.log(treeLon);

		var pointCloudFile = 'data/csv_out_deck/';
		var pointCloudFile = pointCloudFile.concat(treeID);
		var pointCloudFile = pointCloudFile.concat('.json');

		map.addLayer(new MapboxLayer({
	    	id: 'tree',
	    	type: PointCloudLayer,
	    	data: pointCloudFile,
	    	coordinateSystem: COORDINATE_SYSTEM.METER_OFFSETS,
    		coordinateOrigin: [treeLat, treeLon],
	    	getPosition: d => [d[0]/3.28, d[1]/3.28, (d[2])],
	    	getColor: d => [ d[3]*255, (d[3]*125+(d[3]*225*(d[5]-d[4]+1))), d[3]*255, 100*(d[5]-d[4])+100 ],
	    	sizeUnits: 'feet',
	    	pointSize: 3,
	    	opacity: 0.75,
	    	visible: true
	    	}));

		var hours = positions[parseInt(document.getElementById('pickedSeason').value)];
		for (let hour of hours) {
			shadow(treeID,treeLat,treeLon,hour[0],hour[1],hour[2],hour[3],hour[4]);
			};
		
		var species = e.features[0].properties['spc_common'];
		document.getElementById("common").innerHTML = species;
		var link =  'https://www.designacrossscales.org/public_test/html/'.concat(species,'.html');
		document.getElementById("common").setAttribute("href", link);  
		document.getElementById("latin").innerHTML = e.features[0].properties['spc_latin'];
		document.getElementById("address").innerHTML = e.features[0].properties['address'];
		document.getElementById("zipcode").innerHTML = e.features[0].properties['zipcode'];
		document.getElementById("borough").innerHTML = e.features[0].properties['boroname'];
		document.getElementById("curb").innerHTML = e.features[0].properties['curb_loc'];
		document.getElementById("lat").innerHTML = e.features[0].properties['Latitude'];
		document.getElementById("lon").innerHTML = e.features[0].properties['longitude'];
		document.getElementById("status").innerHTML = e.features[0].properties['status'];
		document.getElementById("health").innerHTML = e.features[0].properties['health'];
		document.getElementById("trunk").innerHTML = e.features[0].properties['tree_dbh'];

		var expected = ((((((((e.features[0].properties['tree_dbh'])/12)/3.28)/2)**2)*3.1415926)*28.2+7)/2)*3.28;
		document.getElementById("canopy").innerHTML = expected;

		/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
		//parse xyz json to get tree stats

		jQuery.when(jQuery.getJSON(pointCloudFile)).done( function(treeTable) {
			//console.log(treeTable);
			var max = 0;
			var min = 10;
			var count = 0;
			for (var i = 0; i < treeTable.length; i++) { 
				if ( treeTable[i][0] >= -expected/4 && treeTable[i][0] <= expected/4 && treeTable[i][1] >= -expected/4 && treeTable[i][1] <= expected/4 ) {
					count++;
					if ( treeTable[i][2] >= max ) {
						max = treeTable[i][2];
						}
					else {
						continue;
						};
					if ( treeTable[i][2] <= min ) {
						min = treeTable[i][2];
						}
					else {
						continue;
						};
					}
				else {
					continue;
					}; 
				};
			document.getElementById("height").innerHTML = (max - min)*3.28;
			document.getElementById("density").innerHTML = (max - min)*3.28/count;
			});		

		/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


		});

	
	document.getElementById('pickedSeason').addEventListener('change', function(f) {
		map.removeLayer('shadow1');
		map.removeLayer('shadow2');
		map.removeLayer('shadow3');
		map.removeLayer('shadow4');
		map.removeLayer('shadow5');
		map.removeLayer('shadow6');
		map.removeLayer('shadow7');
		map.removeLayer('shadow8');
		map.removeLayer('shadow9');
		map.removeLayer('shadow10');
		map.removeLayer('shadow11');
		map.removeLayer('shadow12');
		map.removeLayer('shadow13');
		map.removeLayer('shadow14');
		map.removeLayer('shadow15');
		//map.removeLayer('shadowundefined');

		var hours = positions[parseInt(document.getElementById('pickedSeason').value)];
		for (let hour of hours) {
			shadow(treeID,treeLat,treeLon,hour[0],hour[1],hour[2],hour[3],hour[4]);
			};
		});


	var positions = [
					[
						[63,5,0.3,'1',true],
						[72,16,0.4,'2',true],
						[81,27,0.5,'3',true],
						[90,38,0.6,'4',true],
						[101,49,0.7,'5',true],
						[116,60,0.8,'6',true],
						[141,69,0.9,'7',true],
						[182,73,1,'8',true],
						[222,68,0.9,'9',true],
						[245,59,0.8,'10',true],
						[260,48,0.7,'11',true],
						[271,37,0.6,'12',true],
						[280,26,0.5,'13',true],
						[289,15,0.4,'14',true],
						[298,4,0.3,'15',true]
					],

					[
						[1,1,0.3,'1',false],
						[1,1,0.4,'2',false],
						[99,11,0.5,'3',true],
						[109,22,0.6,'4',true],
						[122,32,0.7,'5',true],
						[137,41,0.8,'6',true],
						[156,47,0.9,'7',true],
						[179,50,1,'8',true],
						[201,48,0.9,'9',true],
						[221,42,0.8,'10',true],
						[237,33,0.7,'11',true],
						[249,23,0.6,'12',true],
						[269,12,0.5,'13',true],
						[1,1,0.4,'14',false],
						[1,1,0.3,'15',false]
					],

					[
						[1,1,0,'1',false],
						[1,1,0.4,'2',false],
						[128,6,0.5,'3',true],
						[139,14,0.6,'4',true],
						[152,20,0.7,'5',true],
						[166,25,0.8,'6',true],
						[181,26,0.9,'7',true],
						[196,24,1,'8',true],
						[210,20,0.9,'9',true],
						[223,13,0.8,'10',true],
						[233,5,0.7,'11',true],
						[243,5,0.6,'12',false],
						[1,1,0.5,'13',false],
						[1,1,0.4,'14',false],
						[1,1,0,'15',false]
					],

					[
						[1,1,0,'1',false],
						[1,1,0.4,'2',false],
						[128,6,0.5,'3',false],
						[139,14,0.6,'4',false],
						[152,20,0.7,'5',false],
						[166,25,0.8,'6',false],
						[181,26,0.9,'7',false],
						[196,24,1,'8',false],
						[210,20,0.9,'9',false],
						[223,13,0.8,'10',false],
						[233,5,0.7,'11',false],
						[243,5,0.6,'12',false],
						[1,1,0.5,'13',false],
						[1,1,0.4,'14',false],
						[1,1,0,'15',false]
					]
				];

});





