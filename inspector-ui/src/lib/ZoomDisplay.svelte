<script>
  import { mapZoomLevel } from "./stores.js";
</script>

<template lang="pug">
  div.zoom
    span {$mapZoomLevel}
    label Current Zoom
</template>


<style>
  .zoom {
    display: flex;
    flex-direction: column;
    justify-content: center;
    width: fit-content;
    align-items: center;
    justify-content: space-evenly;
  }

  .zoom span {
    font-size: 60px;
    font-weight: bold;
  }
</style>
