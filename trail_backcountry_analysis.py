#!/usr/bin/env python3
"""
Configurable Trail Buffer Analysis Script

This script allows you to configure:
- Which shapefiles to use for buffering (roads, railways, or both)
- Buffer distance in miles
- Minimum trail segment length to include in results
"""

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge, unary_union
import json
import os
import argparse
from pathlib import Path

def read_specific_shapefiles(data_dir, include_roads=True, include_railways=True):
    """Read specific shapefiles from the washington directory."""
    washington_dir = Path(data_dir) / "washington"
    
    shapefiles_to_read = []
    if include_roads:
        roads_shp = washington_dir / "gis_osm_roads_free_1.shp"
        if roads_shp.exists():
            shapefiles_to_read.append(('roads', roads_shp))
    
    if include_railways:
        railways_shp = washington_dir / "gis_osm_railways_free_1.shp"
        if railways_shp.exists():
            shapefiles_to_read.append(('railways', railways_shp))
    
    if not shapefiles_to_read:
        raise ValueError("No valid shapefiles selected")
    
    print(f"Reading {len(shapefiles_to_read)} shapefile(s):")
    for file_type, shp in shapefiles_to_read:
        print(f"  - {shp.name} ({file_type})")
    
    combined_features = []
    
    # Road types to exclude from buffer generation
    excluded_road_types = {'footway', 'path', 'pedestrian', 'steps', 'bridleway'}
    
    for file_type, shapefile in shapefiles_to_read:
        try:
            gdf = gpd.read_file(shapefile)
            
            # Filter out excluded road types if this is a roads file
            if file_type == 'roads' and 'fclass' in gdf.columns:
                original_count = len(gdf)
                gdf = gdf[~gdf['fclass'].isin(excluded_road_types)]
                filtered_count = original_count - len(gdf)
                if filtered_count > 0:
                    print(f"  Excluded {filtered_count} features with road types: {', '.join(excluded_road_types)}")
            
            # Ensure we have a consistent CRS for buffering (use UTM Zone 10N for Washington)
            if gdf.crs != 'EPSG:32610':
                gdf = gdf.to_crs('EPSG:32610')
            combined_features.append(gdf)
            print(f"Loaded {len(gdf)} features from {shapefile.name}")
        except Exception as e:
            print(f"Error reading {shapefile}: {e}")
    
    if combined_features:
        # Combine all features into a single GeoDataFrame
        combined_gdf = pd.concat(combined_features, ignore_index=True)
        return combined_gdf
    else:
        raise ValueError("No valid shapefiles found")

def create_buffers(gdf, buffer_distance_miles=5):
    """Create buffers around all features."""
    # Convert miles to meters (1 mile = 1609.34 meters)
    buffer_distance_meters = buffer_distance_miles * 1609.34
    
    print(f"Creating {buffer_distance_miles}-mile buffers around {len(gdf)} features...")
    
    # Create buffers
    buffered_geometries = gdf.geometry.buffer(buffer_distance_meters)
    
    # Return individual buffers instead of combining into one
    return buffered_geometries

def read_trails_shapefile(data_dir):
    """Read the trails shapefile."""
    trails_path = Path(data_dir) / "trails" / "Trails.shp"
    
    if not trails_path.exists():
        raise FileNotFoundError(f"Trails shapefile not found at {trails_path}")
    
    trails_gdf = gpd.read_file(trails_path)
    print(f"Loaded {len(trails_gdf)} trail features")
    
    # Convert to UTM Zone 10N for consistent analysis
    if trails_gdf.crs != 'EPSG:32610':
        trails_gdf = trails_gdf.to_crs('EPSG:32610')
    
    return trails_gdf

def find_non_intersecting_segments(trails_gdf, buffer_geometries, min_length_miles=0.1):
    """Find trail segments that don't intersect with any of the buffers."""
    print(f"Finding trail segments that don't intersect with buffers (min length: {min_length_miles} miles)...")
    
    min_length_meters = min_length_miles * 1609.34
    non_intersecting_trails = []
    
    # Combine all buffer geometries for intersection testing
    combined_buffer = unary_union(buffer_geometries)
    
    for idx, trail in trails_gdf.iterrows():
        geom = trail.geometry
        
        if geom is None:
            continue
            
        # Check if the trail intersects with any buffer
        if not geom.intersects(combined_buffer):
            # Trail doesn't intersect - check if it's long enough
            if geom.length >= min_length_meters:
                non_intersecting_trails.append(trail)
        else:
            # Trail intersects - find segments that don't intersect
            if isinstance(geom, LineString):
                try:
                    # Use difference operation to get parts outside the buffer
                    non_intersecting_part = geom.difference(combined_buffer)
                    
                    if not non_intersecting_part.is_empty:
                        # Handle different geometry types returned by difference
                        segments_to_add = []
                        if isinstance(non_intersecting_part, LineString):
                            if non_intersecting_part.length >= min_length_meters:
                                segments_to_add.append(non_intersecting_part)
                        elif isinstance(non_intersecting_part, MultiLineString):
                            for line in non_intersecting_part.geoms:
                                if line.length >= min_length_meters:
                                    segments_to_add.append(line)
                        
                        # Create new trail records for each valid segment
                        for segment in segments_to_add:
                            new_trail = trail.copy()
                            new_trail.geometry = segment
                            non_intersecting_trails.append(new_trail)
                            
                except Exception as e:
                    print(f"Error processing trail {idx}: {e}")
                    continue
            
            elif isinstance(geom, MultiLineString):
                # For MultiLineString, check each line separately
                for line in geom.geoms:
                    if not line.intersects(combined_buffer):
                        if line.length >= min_length_meters:
                            new_trail = trail.copy()
                            new_trail.geometry = line
                            non_intersecting_trails.append(new_trail)
                    else:
                        try:
                            non_intersecting_part = line.difference(combined_buffer)
                            if not non_intersecting_part.is_empty:
                                segments_to_add = []
                                if isinstance(non_intersecting_part, LineString):
                                    if non_intersecting_part.length >= min_length_meters:
                                        segments_to_add.append(non_intersecting_part)
                                elif isinstance(non_intersecting_part, MultiLineString):
                                    for sub_line in non_intersecting_part.geoms:
                                        if sub_line.length >= min_length_meters:
                                            segments_to_add.append(sub_line)
                                
                                for segment in segments_to_add:
                                    new_trail = trail.copy()
                                    new_trail.geometry = segment
                                    non_intersecting_trails.append(new_trail)
                                    
                        except Exception as e:
                            print(f"Error processing multiline segment {idx}: {e}")
                            continue
    
    if non_intersecting_trails:
        result_gdf = gpd.GeoDataFrame(non_intersecting_trails)
        result_gdf.reset_index(drop=True, inplace=True)
        
        # Ensure the result GeoDataFrame has a CRS
        if result_gdf.crs is None:
            result_gdf = result_gdf.set_crs('EPSG:32610')
        
        print(f"Found {len(result_gdf)} non-intersecting trail segments")
        return result_gdf
    else:
        print("No non-intersecting trail segments found")
        # Return an empty GeoDataFrame with the correct CRS
        return gpd.GeoDataFrame(crs='EPSG:32610')

def save_geojson(gdf, output_path):
    """Save GeoDataFrame as GeoJSON."""
    # Ensure the GeoDataFrame has a CRS before transformation
    if gdf.crs is None:
        # Assume UTM Zone 10N if no CRS is set
        gdf = gdf.set_crs('EPSG:32610')
    
    # Convert back to WGS84 for GeoJSON
    gdf_wgs84 = gdf.to_crs('EPSG:4326')
    gdf_wgs84.to_file(os.path.join("output", output_path), driver='GeoJSON')
    print(f"Saved {len(gdf)} trail segments to {output_path}")

def save_buffer_geojson(buffer_geometries, output_path, crs='EPSG:32610'):
    """Save buffer geometries as GeoJSON."""
    # Create a GeoDataFrame from the buffer geometries
    data = [{'id': i+1} for i in range(len(buffer_geometries))]
    buffer_gdf = gpd.GeoDataFrame(data, geometry=buffer_geometries, crs=crs)
    
    # Ensure the GeoDataFrame has a CRS before transformation
    if buffer_gdf.crs is None:
        buffer_gdf = buffer_gdf.set_crs(crs)
    
    # Convert to WGS84 for GeoJSON
    buffer_gdf_wgs84 = buffer_gdf.to_crs('EPSG:4326')
    
    # Save as GeoJSON
    buffer_gdf_wgs84.to_file(os.path.join("output", output_path), driver='GeoJSON')
    print(f"Saved {len(buffer_geometries)} buffer geometries to {output_path}")

def compute_longest_trails(gdf):
    """Compute and display information about the longest trails, grouped by trail name."""
    if gdf.empty:
        print("No trails to analyze")
        return
    
    print("\nAnalyzing trail lengths...")
    
    # Calculate length for each trail segment
    gdf['length_miles'] = gdf.geometry.length / 1609.34  # Convert meters to miles
    
    # Create a copy for grouping
    gdf_copy = gdf.copy()
    
    # Find the trail name column
    trail_name_col = None
    for col in ['name', 'NAME', 'trail_name', 'TRAIL_NAME']:
        if col in gdf_copy.columns:
            trail_name_col = col
            break
    
    if trail_name_col is None:
        print("No trail name column found. Showing individual segments.")
        # Fall back to original behavior
        sorted_trails = gdf_copy.sort_values('length_miles', ascending=False)
        
        print(f"\nTop {len(sorted_trails):,} longest non-intersecting trail segments:")
        print(f"{'Rank':<5} {'Length (miles)':<15} {'Trail Info'}")
        print("-" * 60)
        
        for i, (idx, trail) in enumerate(sorted_trails.iterrows()):
            trail_info = f"Trail {idx}"
            print(f"{i+1:<5} {trail['length_miles']:<15.2f} {trail_info}")
        
        total_length = gdf_copy['length_miles'].sum()
        print(f"\nTotal length of non-intersecting trail segments: {total_length:.2f} miles")
        print(f"Average segment length: {gdf_copy['length_miles'].mean():.2f} miles")
        return
    
    # Group by trail name and sum lengths
    trail_groups = gdf_copy.groupby(trail_name_col).agg({
        'length_miles': 'sum',
        'geometry': 'count'  # Count number of segments
    }).rename(columns={'geometry': 'segment_count'})
    
    # Sort by total length
    trail_groups = trail_groups.sort_values('length_miles', ascending=False)
    
    print(f"\nTop {len(trail_groups):,} longest trails (grouped by name):")
    print(f"{'Rank':<5} {'Total Length (miles)':<20} {'Segments':<10} {'Trail Name'}")
    print("-" * 80)
    
    for i, (trail_name, data) in enumerate(trail_groups.iterrows()):
        # Handle NaN trail names
        if pd.isna(trail_name) or trail_name == "":
            trail_name = "Unnamed Trail"
        
        print(f"{i+1:<5} {data['length_miles']:<20.2f} {data['segment_count']:<10} {trail_name}")
    
    # Also show individual segments for context
    print(f"\nIndividual trail segments (top 10):")
    print(f"{'Rank':<5} {'Length (miles)':<15} {'Trail Name'}")
    print("-" * 50)
    
    sorted_segments = gdf_copy.sort_values('length_miles', ascending=False).head(10)
    for i, (idx, trail) in enumerate(sorted_segments.iterrows()):
        trail_name = trail[trail_name_col] if pd.notna(trail[trail_name_col]) else "Unnamed Trail"
        print(f"{i+1:<5} {trail['length_miles']:<15.2f} {trail_name}")
    
    total_length = gdf_copy['length_miles'].sum()
    total_trails = len(trail_groups)
    total_segments = len(gdf_copy)
    
    print(f"\nSummary:")
    print(f"Total length of non-intersecting trail segments: {total_length:.2f} miles")
    print(f"Number of unique trails: {total_trails}")
    print(f"Number of trail segments: {total_segments}")
    print(f"Average trail length: {total_length/total_trails:.2f} miles")
    print(f"Average segment length: {gdf_copy['length_miles'].mean():.2f} miles")

def main():
    """Main function to execute the trail buffer analysis."""
    parser = argparse.ArgumentParser(description='Trail Buffer Analysis')
    parser.add_argument('--buffer-miles', type=float, default=1.0, 
                       help='Buffer distance in miles (default: 1.0)')
    parser.add_argument('--min-segment-miles', type=float, default=0.1,
                       help='Minimum trail segment length in miles (default: 0.1)')
    parser.add_argument('--no-roads', action='store_true',
                       help='Exclude roads from buffer analysis')
    parser.add_argument('--no-railways', action='store_true', 
                       help='Exclude railways from buffer analysis')
    
    args = parser.parse_args()
    
    data_dir = "input"
    
    try:
        # Step 1: Read Washington shapefiles and create buffers
        print("Step 1: Reading Washington shapefiles...")
        washington_gdf = read_specific_shapefiles(
            data_dir, 
            include_roads=not args.no_roads,
            include_railways=not args.no_railways
        )
        
        print(f"Step 2: Creating {args.buffer_miles}-mile buffers...")
        buffer_geometries = create_buffers(washington_gdf, buffer_distance_miles=args.buffer_miles)
        
        # Save buffer geometries as GeoJSON
        print(f"Step 2a: Saving buffer geometries")
        save_buffer_geojson(buffer_geometries, f'{int(args.buffer_miles)}_mile_buffer.geojson')
        
        # Step 2: Read trails shapefile
        print("Step 3: Reading trails shapefile...")
        trails_gdf = read_trails_shapefile(data_dir)
        
        # Step 3: Find non-intersecting segments
        print("Step 4: Finding non-intersecting trail segments...")
        non_intersecting_gdf = find_non_intersecting_segments(
            trails_gdf, 
            buffer_geometries, 
            min_length_miles=args.min_segment_miles
        )
        
        if not non_intersecting_gdf.empty:
            # Step 4: Save to GeoJSON
            print("Step 5: Saving results to GeoJSON...")
            save_geojson(non_intersecting_gdf, f'{int(args.buffer_miles)}_mile_backcountry_trails.geojson')
            
            # Step 5: Compute longest trails
            print("Step 6: Computing longest trails...")
            compute_longest_trails(non_intersecting_gdf)
        else:
            print("No non-intersecting trail segments found. No output file created.")
            print("\nTry reducing the buffer distance or minimum segment length.")
        
        print("\nAnalysis complete!")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        raise

if __name__ == "__main__":
    main()