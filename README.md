# aws-naip-tile-server
The National Agriculture Imagery Program (NAIP) imagery program acquires aerial imagery during the agricultural growing seasons in the United States.  A primary goal of the NAIP program is to make digital ortho-photography available to the public (and government agencies) within a year of acquisition.   My experience with NAIP as a GIS professional for many years is that:

>  A singular, comprehensive, performant, and dependable source of NAIP
> imagery, that is readily usable by the masses, does not exist today

The purpose of this repository is to create a simple AWS Lambda function & API that can generate 'slippy-map' tiles that can be used in most modern web GIS frameworks and desktop GIS apps.

**DISCLAIMER:** I have worked on this project during downtime between employment.  I have not used the AWS Lambda function and/or API in any real-world applications (yet).  It's worked great in the light experimentation I have done with it - but this should be considered an alpha-level product.

## Table of Contents
<!-- TOC -->
  - [Some Background](#some-background)
  - [Dev Environment](#dev-environment)
  - [Deployment](#deployment)
  - [Usage](#usage)
  - [Admin CLI](#admin-cli)
  - [Known Limitations](#known-limitations)
<!-- /TOC -->

## Some Background

### NAIP Imagery Availability
![naip_coverage_by_year](https://github.com/rmferraro/aws-naip-tile-server/assets/4007906/96c60aed-0e5f-4400-bc81-0a8e286892b3)


NAIP Imagery is available from many places,  in many formats, but most are quite inconvenient...  Lets take a look at a few that I know of:

 1. [USDA Box Hosting:](https://nrcs.app.box.com/v/naip)  Imagery delivered in MrSID format - which is not a driver that is enabled in recent versions of GDAL/RasterIO.  I've also found the Box API very frustrating to just download imagery zip files
 2. [Google Earth Engine:](https://developers.google.com/earth-engine/datasets/catalog/USDA_NAIP_DOQQ)  Very restrictive terms of service
 3. [USDA ArcGIS Server:](https://gis.apfo.usda.gov/arcgis/rest/services/NAIP)  Among other issues, only most recent imagery per state is available
 4. [AWS Registry of Open Data](https://registry.opendata.aws/naip/): NAIP imagery from 2011 to 2021 available in public S3 buckets, in various formats.  But S3 buckets are Requestor Pays

Of the above sources, the AWS Registry of Open Data is by far the most readily usable.  But usage is still not a trivial.  There are 1 million+ geotiffs in the visualization bucket alone...  We're looking at hundreds of TB of data...  And the geotiffs are provided as digital ortho quarter quad tiles (DOQQs) projected into multiple UTM coordinate systems.

### Why AWS Lambda?
I've already attempted to justify using AWS Registry of Open Data.  Without getting into the specifics of the AWS pricing model - copying this imagery to some other hosting platform would seem to be a non-starter for many potential use cases.   So for lack of a better explanation, I consider this source of NAIP imagery 'tightly-coupled' to the AWS platform, and therefore using the full suite of AWS tools/magic makes sense.

## Dev Environment

### pre-requisites

 - [Poetry](https://python-poetry.org/):  Python package/environment management
 - [GNU Make](https://www.gnu.org/software/make/):  This is required by AWS SAM CLI to package up Lambda Layers

### setup
With pre-requisites satisfied, from the root of this repo:

    poetry install

If you haven't done so already, run `aws configure`.

And then run the unit test-suite (Integration test-suite can't be run until you have a successful deployment)

    pytest tests/unit

## Deployment
Since the project uses AWS SAM CLI - deployment is very simple:

    rm -R .aws-sam && poetry export --without-hashes -o requirements.txt && sam build && rm requirements.txt && sam deploy

 Assuming a successful deployment - you should see something like this in your terminal.

    CloudFormation outputs from deployed stack
    -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    Outputs
    -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    Key                 NAIPTileCache
    Description         NAIPTileCache S3 Bucket
    Value               aws-naip-tile-server-naiptilecache-1ke1562nf5zig

    Key                 NAIPLambdaIamRole
    Description         NAIPLambdaRole ARN
    Value               arn:aws:iam::109906859411:role/aws-naip-tile-server-NAIPLambdaRole-EHD9DVRX3OOB

    Key                 NAIPTileFunction
    Description         NAIPTileFunction Lambda Function ARN
    Value               arn:aws:lambda:us-west-2:109906859411:function:get-naip-tile

    Key                 NAIPTileApi
    Description         API Gateway endpoint URL for Prod stage for NAIPTileFunction
    Value               https://dxw60vz69c.execute-api.us-west-2.amazonaws.com/prod/tile
    -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    Successfully created/updated stack - aws-naip-tile-server in us-west-2

Of particular importance is the `NAIPTileApi` key.  This is the tile api...

## Usage
**NOTE:**  If a request is made for a tile where there is no NAIP imagery for the specific year requested, a HTTP 404 Not Found response status code will be returned by the Lambda function

### HTTP API

    https://{XYZTileApi.Value}/prod/tile/{year}/{z}/{y}/{x}
	https://dxw60vz69c.execute-api.us-west-2.amazonaws.com/prod/tile/2021/11/776/425

### Python + boto3

      import base64
      import boto3
      import json
      from io import BytesIO
      from PIL import Image

      lambda_client = boto3.client('lambda')
      request_payload = {'year':2021,'z':11,'y':776,'x':425}
      response = lambda_client.invoke(
           FunctionName="get-naip-tile",
           InvocationType="RequestResponse",
           Payload=json.dumps(request_payload)
      )
      response_payload = json.loads(response["Payload"].read().decode("utf-8"))
      tile_image = Image.open(BytesIO(base64.b64decode(response_payload["body"])))

## Admin CLI
There is a CLI available to perform admin-like actions that I feel are best done locally. To see a list of available commands, run:
`python admin_cli.py --help`.

Output:

    Usage: admin_cli.py [OPTIONS] COMMAND [ARGS]...

      CLI tool to perform admin actions

    Options:
      --help  Show this message and exit.

    Commands:
      seed-cache  Seed Tile Cache for specific areas/years.

To get detailed info about specific commands:
`python admin_cli.py [@command] --help`

Example output for `seed-cache` command

    Usage: admin_cli.py seed-cache [OPTIONS]

      Seed Tile Cache for specific areas/years.

    Options:
      --from_zoom INTEGER  Zoom level cache-ing will start at
      --to_zoom INTEGER    Zoom level cache-ing will end at  [required]
      -y, --years INTEGER  NAIP years to cache
      --coverage TEXT      WKT geometry (WGS84) of ground area to cache tiles for
      --dry-run            Only print summary of how many tiles would be cached
      --help               Show this message and exit.

### Commands

#### seed-cache

    Usage: admin_cli.py seed-cache [OPTIONS]

      Seed Tile Cache for specific areas/years.

    Options:
      --from_zoom INTEGER  Zoom level cache-ing will start at
      --to_zoom INTEGER    Zoom level cache-ing will end at  [required]
      -y, --years INTEGER  NAIP years to cache
      --coverage TEXT      WKT geometry (WGS84) of ground area to cache tiles for
      --dry-run            Only print summary of how many tiles would be cached
      --help               Show this message and exit.

This command will seed S3TileCache for specific areas/years.  Cacheing lower zoom levels will mitigate this [known limitation](#degrading-performance-for-lower-zoom-levels)


## Known Limitations
### Only using `naip-visualization` bucket
My primary goal was to use NAIP imagery for a basemap, so the `naip-visualization` bucket is most practical for this application.  Currently, there is no way to generate tiles for imagery in the `naip-analytic` or `naip-source` buckets.
### Redundant Tile Creation
It's possible that multiple requests for the same tile could be made at the same time. In the case the tile already exists in the s3 tile cache, there are no issues... But if the tile does not exist in the s3 tile cache, there would be redundant tile creation. The primary issue with redundant tile creation is increased lambda run time, which will cost more $$$. I currently perceive this to be a very minor potential issue... Even implementing some type of lock/wait to prevent redundant tile creation won't decrease lambda run time - because instead of building the tile - the lambda function will be running but idle...
### Degrading Performance for Lower Zoom Levels
NAIP imagery in the `naip-visualization` S3 bucket have full-resolution data with 5 levels of overviews. This means that NAIP data can be read most efficiently at six zoom levels, in this case zooms 12-17.  Once we drop below zoom level 12, many images need to be combined and downsampled **on the fly**.  For example, to create an image for a single zoom 6 tile, you'd need to read _4,096_ times more data at level 12, then downsample.  In my opinion, NAIP is not particularly great for low zoom levels; it often appears patchy because of the many different collects and/or mixed resolutions of collects.  So I often use other imagery basemaps for lower level zooms.

One workaround for this is to cache lower zoom levels (<12) using the [seed-cache](#seed-cache) command in the [Admin CLI](#admin-cli)
### Spatial Queries on Bundled Parquet File
When a tile is requested, a spatial query is necessary to determine what geotiffs intersect the tile's geometry.  In the current implementation, a parquet index file is bundled in the `src.data` module and used for this purpose.  I chose this approach vs maintaining an index in a separate database of some sort - for simplicity's sake.  I'm fairly confident a spatial query executed against a postgis table would complete quicker than the equivalent parquet query.  So if/when the time comes to chase maximum performance - this is a good place to start...
### Inefficient AWS Lambda Usage
For tiles that are already cached - calling the Lambda function seems inefficient; why not just fetch the tile from S3 directly?  Particularly on cold starts - the extra latency (and Lambda $$$) is avoidable.
