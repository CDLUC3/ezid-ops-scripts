# RGPO to EZID Conversion Script

Script for transforming grant data from RGPO (Research Grants Program Office) CSV exports into the format required by the EZID batch3.py registration script.

## Overview

This script converts grant information from RGPO's export format to the specific CSV structure required by EZID's batch registration process. It handles essential metadata transformations and optionally provides ROR (Research Organization Registry) identifier matching for institutional affiliations.

## Installation

```
pip install requests
```

## Usage

Basic usage:
```
python convert_rgpo_file_to_ezid_batch_format.py -i input_file.csv -o output_file.csv
```

With ROR affiliation matching enabled:
```
python convert_rgpo_file_to_ezid_batch_format.py -i input_file.csv -o output_file.csv -m
```

### Arguments

- `-i, --input`: Path to the input CSV file (RGPO export)
- `-o, --output`: Path to the desired output CSV file
- `-m, --match-affiliations`: Enable ROR affiliation matching for Institution Names

## Input Requirements

The input CSV must contain at least these columns:
- Application ID
- Project Title

Additional columns used if available:
- Institution Name
- Principal Investigator
- Lay Abstract
- Start Date

## Output Format and Mapping File

The script generates a CSV with the metadata structure required by EZID's batch3.py registration script. Each row in the output follows a template with 35 fields that map to DataCite metadata schema elements.

The included `rgpo_map.txt` file corresponds to this output format and is used by EZID's batch3.py script to register the grants. This mapping file defines how each column in the output CSV maps to specific DataCite metadata fields:

```
_target = $1
_profile = datacite
/resource/creators/creator/creatorName = $2
...
```

Where `$1` through `$35` correspond to the 35 columns in the generated output CSV. The batch3.py script uses this mapping to transform the CSV data into the proper DataCite format for DOI registration.

### Output Field Mapping Logic

The mapping logic applies the following conditionals when transforming RGPO data, using default values appropriate to the grants registration:

1. **Location**: 
   - Value: `https://rgpogrants.ucop.edu/files/1614305/f480589/index.html?appid={Application ID}`
   - Conditional: Only populated if Application ID exists
   - Maps to: `_target` in rgpo_map.txt ($1)

2. **Creator/Publisher Information**: 
   - Static values set to "University of California Office of the President" with ROR identifier
   - Maps to: Creator fields in rgpo_map.txt ($2-$5)

3. **Title**: 
   - Direct mapping from "Project Title" field
   - Maps to: `/resource/titles/title` in rgpo_map.txt ($6)

4. **Publication Year**: 
   - Not automatically populated (empty in template)
   - Maps to: `/resource/publicationYear` in rgpo_map.txt ($11)

5. **Resource Type**: 
   - Static values: General = "Other", Type = "Grant"
   - Maps to: Resource type fields in rgpo_map.txt ($12-$13)

6. **Description**: 
   - Source: "Lay Abstract" field
   - Preprocessing: HTML tags removed, whitespace normalized
   - Conditional: If description exists, "Description Type" field is set to "Abstract"
   - Maps to: Description fields in rgpo_map.txt ($14-$15)

7. **Contributor Information**:
   - "Contributor Type" always set to "ProjectLeader"
   - "Contributor Name" from "Principal Investigator" field
   - Identifier fields left empty
   - Maps to: Contributor fields in rgpo_map.txt ($16-$20)

8. **Affiliation Information**:
   - "Affiliation" from "Institution Name" field
   - ROR matching conditional logic:
     - Only if `-m/--match-affiliations` flag is used
     - "Affiliation Identifier" populated with ROR ID if match found
     - "Affiliation Identifier Scheme" set to "ROR" if match found
     - "Affiliation Identifier Scheme URI" set to "https://ror.org/" if match found
   - Maps to: Affiliation fields in rgpo_map.txt ($21-$24)

9. **Date Information**:
   - "Date" from "Start Date" field
   - Conditional: If date exists, "Date Type" field is set to "Issued"
   - Maps to: Date fields in rgpo_map.txt ($25-$27)

10. **Identifier Information**:
    - "Alternate Identifier" set to Application ID
    - "Alternate Identifier Type" always set to "award-number"
    - Maps to: Identifier fields in rgpo_map.txt ($28-$29)

### ROR Affiliation Matching Logic

When enabled, the script:
1. Queries the ROR API affiliation matching endpoint with the institution name
2. Processes the API response to find if a result with "chosen" exists (i.e. a match is found)
3. If a match is found with sufficient score, populates the affiliation identifier fields
4. Logs all API interactions and results to the log file

## Logs

When affiliation matching is enabled, the script creates a log file with the naming format: `YYYYMMDD_HHMMSS_affiliation_matching.log`

### Log Contents
- API query URLs
- Response status and errors
- Match results and scores
- Processing exceptions