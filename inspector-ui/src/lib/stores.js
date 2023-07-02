import { writable } from 'svelte/store';

export const mapZoomLevel = writable(parseInt(import.meta.env.VITE_INITIAL_VIEW_ZOOM));
export const selectedYear = writable(2011);
export const rawTileLoads = writable([]);
