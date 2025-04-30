#!/usr/bin/env python

import os
import sys
import json

def inspect_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print("\nJSON Structure:")
        print(json.dumps(data, indent=2))
        
        # Check for specific keys
        print("\nKeys at root level:")
        for key in data.keys():
            print(f"- {key}")
            
        # Check for attributes
        if 'attributes' in data:
            print("\nAttributes:")
            for attr_key in data['attributes'].keys():
                print(f"- {attr_key}")
                
            # Check for TAG
            if 'TAG' in data['attributes']:
                print("\nTags:")
                for tag_key, tag_value in data['attributes']['TAG'].items():
                    if isinstance(tag_value, dict) and 'name' in tag_value:
                        print(f"  - {tag_value['name']}")
        
        # Check for artist
        if 'artist' in data:
            print("\nArtists:")
            for artist in data['artist']:
                print(f"- {artist}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_json.py <path_to_contentV2.json>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        sys.exit(1)
        
    inspect_json(file_path)
