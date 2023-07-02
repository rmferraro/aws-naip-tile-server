<script>
  import * as d3 from "d3";
  import Highcharts from "highcharts";
  import { tick } from "svelte";
  import { rawTileLoads } from "./stores.js";

  let tileLoadSummaries = [];

  $: $rawTileLoads,
    (async () => {
      if ($rawTileLoads.length > 0) {
        let minLoadTime = Infinity,
          maxLoadTime = -Infinity;

        let elapsedByZoom = {};
        $rawTileLoads.forEach(function (tileLoad) {
          minLoadTime = Math.min(minLoadTime, tileLoad.elapsed);
          maxLoadTime = Math.max(maxLoadTime, tileLoad.elapsed);

          if (!elapsedByZoom.hasOwnProperty(tileLoad.z))
            elapsedByZoom[tileLoad.z] = [];
          elapsedByZoom[tileLoad.z].push(tileLoad.elapsed);
        });

        tileLoadSummaries = Object.entries(elapsedByZoom).map(([k, v]) => ({
          zoom: k,
          min: Math.min(...v).toFixed(2),
          max: Math.max(...v).toFixed(2),
          tiles: v.length,
          binnedLoadTimes: binLoadTimes(v, [minLoadTime, maxLoadTime]),
        }));

        await tick();
        drawSparklinePlots();
      }
    })();

  const binLoadTimes = (loadTimes, range) => {
    var histGenerator = d3.bin().domain(range).thresholds(19);
    var bins = histGenerator(loadTimes);
    return bins.map((b) => b.length);
  };

  const drawSparklinePlots = () => {
    const tds = Array.from(document.querySelectorAll("td[data-sparkline]"));
    for (let i = 0; i < tds.length; i += 1) {
      const td = tds[i];
      const stringdata = td.dataset.sparkline;
      const data = stringdata.split(",").map(parseFloat);
      const chart = {
        chart: {
          renderTo: td,
          backgroundColor: null,
          borderWidth: 0,
          type: "area",
          margin: [2, 0, 2, 0],
          width: 120,
          height: 20,
          style: {
            overflow: "visible",
          },
          // small optimalization, saves 1-2 ms each sparkline
          skipClone: true,
        },
        title: {
          text: "",
        },
        credits: {
          enabled: false,
        },
        xAxis: {
          labels: {
            enabled: false,
          },
          title: {
            text: null,
          },
          startOnTick: false,
          endOnTick: false,
          tickPositions: [],
        },
        yAxis: {
          endOnTick: false,
          startOnTick: false,
          labels: {
            enabled: false,
          },
          title: {
            text: null,
          },
          tickPositions: [0],
        },
        legend: {
          enabled: false,
        },
        tooltip: {
          enabled: false,
        },
        plotOptions: {
          series: {
            animation: false,
            lineWidth: 1,
            shadow: false,

            marker: {
              radius: 0.25,
              states: {
                hover: {
                  enabled: false,
                },
              },
            },
            fillOpacity: 0.25,
          },
          column: {
            negativeColor: "#910000",
            borderColor: "silver",
          },
        },
        series: [
          {
            data: data,
            pointStart: 1,
          },
        ],
      };

      new Highcharts.Chart(td, chart, null);
    }
  };
</script>

<template lang="pug">
  div#table-container
    table
      thead
        tr
          th Zoom
          th Tiles Loaded
          th Min Time
          th Max Time
          th
      tbody
      +if('tileLoadSummaries.length == 0')
        tr
          td.no-summary(colspan=5) No NAIP Tiles Loaded
        +else()
          +each ('tileLoadSummaries as loadSummary')
            tr
              td {loadSummary.zoom}
              td {loadSummary.tiles}
              td {loadSummary.min}
              td {loadSummary.max}
              td(data-sparkline="{loadSummary.binnedLoadTimes.join(',')}")
</template>



<style>
  .no-summary {
    padding-top: 50px;
  }

  #table-container {
    width: 100%;
    overflow: auto;
  }

  table {
    width: 100%;
    position: relative;
  }

  table,
  th,
  td {
    border-collapse: collapse;
    font-size: 14px;
    text-align: center;
  }

  th {
    position: sticky;
    top: 0;
    background-color: #303031;
    z-index: 10;
  }

  th,
  td {
    padding: 5px;
    border-radius: 5px;
  }
</style>
