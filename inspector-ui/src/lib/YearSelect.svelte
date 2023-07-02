<script>
  import { selectedYear } from "./stores.js";
  let years = Array.from({ length: 11 }, (x, i) => 2011 + i);
</script>

<template lang="pug">
  div#year-select
    select(bind:value="{$selectedYear}")
      +each('years as year')
        option {year}
    label NAIP Year
</template>


<style>
  #year-select {
    display: flex;
    flex-direction: column;
    justify-content: center;
    width: fit-content;
    align-items: center;
    justify-content: space-evenly;
  }

  select {
    margin-bottom: 15px;
    height: 40px;
    font-size: 16px;
  }
</style>
