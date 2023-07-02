<script>
  import { onMount } from "svelte";

  import Map from "ol/Map.js";
  import View from "ol/View.js";
  import GeoJSON from "ol/format/GeoJSON.js";
  import { Tile as TileLayer, Vector as VectorLayer } from "ol/layer.js";
  import "ol/ol.css";
  import { fromLonLat } from "ol/proj";
  import { OSM, Vector as VectorSource, XYZ } from "ol/source.js";
  import { Fill, Stroke, Style, Text } from "ol/style.js";

  import Feature from "ol/Feature.js";
  import { fromExtent } from "ol/geom/Polygon";
  import { mapZoomLevel, rawTileLoads, selectedYear} from "./stores.js";

  import coverageSummary from "../json/naip-coverage-summary.json";
  import statesGeojson from "../json/us-states.json";

  import OverviewMap from "./OverviewMap.svelte";

  let tileBoundarySource = new VectorSource();
  let naipTileSource = new XYZ({});
  let statesWithCoverage = new VectorSource();
  let naipTileApi = import.meta.env.VITE_NAIP_TILE_API;

  let currentMapExtent;

  $: $selectedYear,
    (() => {
      naipTileSource.setUrl(`${naipTileApi}/${$selectedYear}/{z}/{y}/{x}`)
      statesWithCoverage.clear();
      statesWithCoverage.addFeatures(getStatesWithNaip($selectedYear));
    })();

  onMount(async () => {
    const initialViewCenter = import.meta.env.VITE_INITIAL_VIEW_CENTER.split(
      ","
    ).map((c) => parseFloat(c));
    const maxZoom = parseInt(import.meta.env.VITE_MAX_ZOOM);
    const minZoom = parseInt(import.meta.env.VITE_MIN_ZOOM);


    const tileBoundaryOutlineStyle = new Style({
      stroke: new Stroke({
        color: "gold",
        width: 3,
      }),
    });
    const tileBoundaryLabelStyle = new Style({
      text: new Text({
        font: "20px Ubuntu,sans-serif",
        overflow: true,
        fill: new Fill({
          color: "#000",
        }),
        stroke: new Stroke({
          color: "#fff",
          width: 3,
        }),
      }),
    });
    const tileBoundaryStyle = [
      tileBoundaryOutlineStyle,
      tileBoundaryLabelStyle,
    ];

    let tileLoads = {};

    const map = new Map({
      target: "the-map",
      layers: [
        new TileLayer({
          source: naipTileSource,
          minZoom: minZoom - 1,
          maxZoom: maxZoom,
        }),
        new VectorLayer({
          source: tileBoundarySource,
          minZoom: minZoom - 1,
          maxZoom: maxZoom,
          style: function (feature) {
            const label = feature.get("name");
            tileBoundaryLabelStyle.getText().setText(label);
            return tileBoundaryStyle;
          },
        }),
        new TileLayer({
          source: new XYZ({
            url: "http://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
          }),
          minZoom: 0,
          maxZoom: minZoom,
        }),
        new VectorLayer({
          source: statesWithCoverage,
          minZoom: 0,
          maxZoom: minZoom,
        }),
      ],
      view: new View({
        constrainResolution: true,
        center: fromLonLat(initialViewCenter),
        zoom: $mapZoomLevel,
      }),
    });

    naipTileSource.on("tileloadstart", function (evt) {
      tileLoads[evt.tile.tileCoord] = { start: Date.now() };
    });

    naipTileSource.on("tileloadend", function (evt) {
      const loadEnd = Date.now();
      let tileLoad = tileLoads[evt.tile.tileCoord];
      const loadStart = tileLoad["start"];
      tileLoad["z"] = evt.tile.tileCoord[0];
      tileLoad["elapsed"] = loadEnd - loadStart;

      let loadedTiles = [];
      for (const [tileCoord, tileLoad] of Object.entries(tileLoads)) {
        if (!tileLoad.hasOwnProperty("elapsed") || tileLoad.elapsed < 0)
          continue;

        loadedTiles.push(tileLoad);
      }
      rawTileLoads.set(loadedTiles);
    });

    map.on("moveend", function () {
      const mapView = map.getView();
      const extent = mapView.calculateExtent(map.getSize());
      const zoom = mapView.getZoom();
      drawVisibleTileGrid(extent,zoom);
      currentMapExtent = extent;
      mapZoomLevel.set(zoom);
    });
  });

  const drawVisibleTileGrid = (extent,zoom) => {
    tileBoundarySource.clear();
      const tileGrid = naipTileSource.getTileGrid();
      tileGrid.forEachTileCoord(extent, zoom, function (tileCoord) {
        tileBoundarySource.addFeature(
          new Feature({
            geometry: fromExtent(tileGrid.getTileCoordExtent(tileCoord)),
            name: `z:${tileCoord[0]} x:${tileCoord[1]} y:${tileCoord[2]}`,
          })
        );
      });
  }

  const getStatesWithNaip = (year) => {
    const coverageStates = coverageSummary[year];
    const geojsonFormatter = new GeoJSON();
    const opts = {
      dataProjection: "EPSG:4326",
      featureProjection: "EPSG:3857",
    };
    const stateFeatures = statesGeojson.features
      .filter((f) => coverageStates.includes(f.id))
      .map((f) => geojsonFormatter.readFeature(f, opts));
    return stateFeatures;
  };
</script>

<template lang="pug">
  div#the-map
  div#ov-container
    OverviewMap(parentMapExtent="{currentMapExtent}")
</template>


<style>
  #the-map {
    width: 100%;
    height: 100%;
    position: relative;
  }
  #ov-container {
    position: absolute;
    top:0;
    right: 0;
    width:300px;
    height: 300px;
  }
</style>
