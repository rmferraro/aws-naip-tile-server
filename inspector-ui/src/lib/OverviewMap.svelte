<script>
  import Feature from "ol/Feature.js";
  import Map from "ol/Map.js";
  import View from "ol/View.js";
  import { defaults } from "ol/control/defaults";
  import { fromExtent } from "ol/geom/Polygon";
  import { defaults as defaultInteractions } from "ol/interaction.js";
  import { Tile as TileLayer, Vector as VectorLayer } from "ol/layer.js";
  import { fromLonLat } from "ol/proj";
  import { Vector as VectorSource, XYZ } from "ol/source.js";
  import { onMount } from "svelte";
  export let parentMapExtent;

  let bboxSource = new VectorSource();
  let map;

  $: {
    if (typeof parentMapExtent !== "undefined") {
      bboxSource.clear();
      bboxSource.addFeature(
        new Feature({
          geometry: fromExtent(parentMapExtent),
        })
      );

      const mapView = map.getView();
      mapView.fit(parentMapExtent, map.getSize());
      mapView.setZoom(mapView.getZoom() - 2);
    }
  }

  onMount(async () => {
    map = new Map({
      target: "ov-map",
      controls: defaults({ zoom: true }),
      interactions: defaultInteractions({
        doubleClickZoom: false,
        dragPan: false,
        keyboard: false,
        mouseWheelZoom: false,
      }),
      layers: [
        new TileLayer({
          source: new XYZ({
            url: "https://services.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
          }),
        }),
        new VectorLayer({
          source: bboxSource,
        }),
      ],
      view: new View({
        constrainResolution: true,
        center: fromLonLat([0, 0]),
        zoom: 7,
      }),
    });
  });
</script>

<template lang="pug">
    div#ov-map
</template>

<style>
  #ov-map {
    width: 100%;
    height: 100%;
    box-shadow: 0px 5px 20px 1px;
  }
</style>
