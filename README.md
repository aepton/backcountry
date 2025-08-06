# What are we doing here?

Backcountry begins five miles from the nearest road. Everything closer to a road than five miles is frontcountry.

I love this definition, because it's simple and effective. You always know where you stand. But, not really. Once you get hiking, which I love, you don't really know how far you are from anything.

This is a definition built for GIS, so let's make some maps! Can we find the trails in Washington state that really get into the backcountry?

# Approach

## Overview

In theory (and, spoiler alert, in practice) this is pretty simple:

1. Get a shapefile of all the roads in Washington state, and another shapefile of all the trails
2. Draw a 5-mile buffer around them (or use another distance, as we'll discuss)
3. For each trail segment, does it intersect with the buffer? If not, it's in the backcountry!

### AI disclosure

I want to say up front that basically all of the code here was written by AI, either Claude Code or Cursor. This is my repo, so I take responsibility for it.

## Initial data

Trails data came from [the Washington Recreation and Conservation Office's 2017 trails database](https://geo.wa.gov/datasets/wa-rco::wa-rco-trails-database-public-view/explore?layer=0&location=47.222544%2C-120.843645%2C7.39), while roads (and railways) came from [Geofabrik's OpenStreetMap mirror for Washington state data](https://download.geofabrik.de/north-america/us/washington.html).

One thing to note is that the OSM data contains a variety of different "road" types - including trails. In our analysis, we want to exclude those; one could also argue we should've just used only OSM data to begin with, but the RCO trails database felt perhaps more authoritative. That said, it's also from 2017, as opposed to the surely-far-more-up-to-date OSM data.

## What's missing from this repo

Due to (reasonable) github file size limits, the washington OSM data will have to be downloaded manually from the above URL. The buffer output files (geojson and shapefile) are also too large, and omitted.

# Implementation

As described in the [Overview](#overview), we first draw a buffer around all the roads, and then iterate over trail segments to determine whether they're outside our computed buffers. We store a geojson file containing the trail segments that pass our criteria, and then generate some stats for each trail based on the preserved segments.

## Excluded road types

At the time this README was written, the following OSM road types were excluded:

```
'footway', 'path', 'pedestrian', 'steps', 'bridleway'
```

Changing these will substantially change the output. For instance, "bridleway" is what OSM calls horse trails, which are somewhat common in the backcountry. For a trail to be 5 miles from a car-road _and_ a horse-road is asking a lot. Perhaps once upon a time, bridleways would have been as disruptive as highways (er...), but in the 21st century it's safe to assume these get effectively zero traffic (double digit users per day on the busiest of them, surely).

## Included railroads

I included railroads in this analysis because I find them almost as disruptive, in their invasion of the natural world by the human-made one, as roads. Ok, far less disruptive, actually - but when I'm out hiking, I'll be just as annoyed by a big cargo train passing by me as if I find myself hiking along a road. So railroads are out (but you can include them by flipping a command-line switch).

## Output

After running the `run_analysis.sh` script, the [/output](/output/) folder in this repo contains the results for a variety of "backcountry" definitions:

* X_mile_backcountry_trails.geojson: all trail segments that meet our definition
* X_mile_buffer.geojson: an artifact we generate containing the buffer from all the roads and railways, useful for visualization and debugging, but pretty ugly and unusable
* X_mile_buffer.dbf/prj/shp/shx: the various components of the shapefile version of X_mile_buffer.geojson, a much more usable (because smaller) but still ugly and unusable artifact
* X_mile_output.txt: the output from running this job for the given backcountry definition. Mostly interesting because it contains an ordered list of trails by how long they spend in the backcountry.

## Backcountry distance

The classic backcountry definition is "5 miles from a road" and you can see what that gets us by looking at [5_mile_output.txt](/output/5_mile_output.txt) - 176 trails, 15 of which spend 10+ miles in the backcountry.

That's honestly pretty good, a very small but still sizable list of trails to go exploring in. It's also a list almost too small to be useful - the vast majority of trails in Washington (22,454 from this database) aren't on it. I added a variety of different distances to get a sense of the continuum of trails. We can now put every trail in the state into a pretty nice continuum of "frontcountry" -> "backcountry", rather than just a simple (and rare) "yes, backcountry" or (almost always) "no".