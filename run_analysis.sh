#!/bin/bash

# Script to run trail backcountry analysis for different buffer distances
# Loops over specified mile values and runs the analysis and conversion commands

# Array of mile values to process
miles=(1 2 3 4 5 10 15)

echo "Starting trail backcountry analysis for multiple buffer distances..."
echo "Processing mile values: ${miles[*]}"
echo ""

# Loop over each mile value
for mile in "${miles[@]}"; do
    echo "=== Processing ${mile} mile buffer ==="
    
    # Run the Python analysis script
    echo "Running Python analysis for ${mile} mile buffer..."
    python trail_backcountry_analysis.py --buffer-miles "${mile}.0" > "output/${mile}_mile_output.txt"
    
    # Check if the Python script completed successfully
    if [ $? -eq 0 ]; then
        echo "Python analysis completed successfully for ${mile} mile buffer"
        
        # Convert GeoJSON to Shapefile
        echo "Converting GeoJSON to Shapefile for ${mile} mile buffer..."
        ogr2ogr -f "ESRI Shapefile" "output/${mile}_mile_buffer.shp" "output/${mile}_mile_buffer.geojson"
        
        if [ $? -eq 0 ]; then
            echo "Shapefile conversion completed successfully for ${mile} mile buffer"
        else
            echo "ERROR: Shapefile conversion failed for ${mile} mile buffer"
        fi
    else
        echo "ERROR: Python analysis failed for ${mile} mile buffer"
    fi
    
    echo ""
done

echo "Analysis complete for all mile values!" 