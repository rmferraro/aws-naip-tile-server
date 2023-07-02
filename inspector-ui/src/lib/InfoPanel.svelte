<script>
  import ZoomDisplay from "./ZoomDisplay.svelte";
  import YearSelect from "./YearSelect.svelte";
  import TileLoadSummary from "./TileLoadSummary.svelte";
  </script>

<template lang="pug">
  div#info-panel-container
    div#info-panel
      div.left
        ZoomDisplay
        YearSelect
      div.right
        TileLoadSummary
</template>


<style>
  #info-panel-container {
    position: absolute;
    height: 200px;
    width: 700px;
    background-color: #303031;
    bottom: 0;
    left: 50%;
    transform: translate(-50%);
    z-index: 5;
    color: white;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    font-family: "Ubuntu";
    padding: 10px;
  }

  #info-panel {
    display: flex;
    flex-direction: row;
    justify-content: space-evenly;
    height: 100%;
  }

  .left {
    display: flex;
    flex-direction: column;
    justify-content: center;
    width: fit-content;
    align-items: center;
    justify-content: space-evenly;
    width: 25%;
  }

  .right {
    display: flex;
    flex-direction: row;
    justify-content: right;
    width: 100%;
    justify-content: space-evenly;
  }
</style>
