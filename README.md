# aws-naip-tile-server
The National Agriculture Imagery Program (NAIP) imagery program acquires aerial imagery during the agricultural growing seasons in the United States.  A primary goal of the NAIP program is to make digital ortho-photography available to the public (and government agencies) within a year of acquisition.   My experience with NAIP as a GIS professional for many years is that:

>  A singular, comprehensive, performant, and dependable source of NAIP
> imagery, that is readily usable by the masses, does not exist today

The purpose of this repository is to create a simple AWS Lambda function & API that can generate 'slippy-map' tiles that can be used in most modern web GIS frameworks and desktop GIS apps.

**DISCLAIMER:** I have worked on this project during downtime between employment, as an opportunity to get some hands on experience with AWS Serverless capabilities.  I have not used the AWS Lambda function and/or API in any real-world applications (yet).  It's worked great in the light experimentation I have done with it - but this should be considered an alpha-level product.

## Table of Contents
<!-- TOC -->

- [aws-naip-tile-server](#aws-naip-tile-server)
    - [Table of Contents](#table-of-contents)
    - [Some Background](#some-background)
        - [NAIP Imagery Availability](#naip-imagery-availability)
        - [Why AWS Lambda?](#why-aws-lambda)
    - [Dev Environment](#dev-environment)
        - [pre-requisites](#pre-requisites)
        - [setup](#setup)
    - [Deployment](#deployment)
        - [Pre-Deployment Configuration](#pre-deployment-configuration)
            - [Enable/Disable S3 Backed Tile Cache](#enabledisable-s3-backed-tile-cache)
        - [Deploying with AWS SAM CLI](#deploying-with-aws-sam-cli)
    - [Usage](#usage)
        - [HTTP API](#http-api)
        - [Python + boto3](#python--boto3)
    - [Admin CLI](#admin-cli)
        - [Command Groups](#command-groups)
            - [cache](#cache)
                - [seed](#seed)
            - [stack](#stack)
                - [delete](#delete)
                - [deploy](#deploy)
                - [status](#status)
    - [Known Limitations](#known-limitations)
        - [Only using naip-visualization bucket](#only-using-naip-visualization-bucket)
        - [Redundant Tile Creation](#redundant-tile-creation)
        - [Degrading Performance for Lower Zoom Levels](#degrading-performance-for-lower-zoom-levels)
        - [Spatial Queries on Bundled Parquet File](#spatial-queries-on-bundled-parquet-file)
        - [Inefficient AWS Lambda Usage](#inefficient-aws-lambda-usage)
    - [naip-inspector-ui](#naip-inspector-ui)

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

And then run the test-suite.  Running the full test-suite requires the AWS Stack to have be deployed successfully.  If the AWS Stack has not been deployed, a significant amount of tests get skipped.

    pytest

## Deployment

### Pre-Deployment Configuration
There are several configuration options:
- **ImageFormat**:  Image format tiles will be returned in.  Acceptable values are JPEG or PNG.  Default is PNG.
- **MaxZoom**:  Max zoom level API will attempt to produce tiles for.  If a tile is requested at a higher zoom level, the API will return a HTTP 400 error.  Default is 20.
- **MinZoom**:  Min zoom level API will attempt to produce tiles for.  If a tile is requested at a lower zoom level, the API will return a HTTP 400 error.  Default is 10.
- **RescalingEnabled**:  Allow missing tiles to be produced from rescaling existing cached tiles.  Default is TRUE.
- **DownscaleMaxZoom**:  If RescalingEnabled==TRUE, the max zoom level where attempts to create missing tiles from downscaling will kick in.  Default is 11.
- **UpscaleMinZoom**:  If RescalingEnabled==TRUE, the min zoom level where attempts to create missing tiles from upscaling will kick in. Default is 18.
- **TileCacheBucket**:  Existing S3 bucket name to be used as tile cache.  This bucket should be owned by the same AWS account deploying the Lambda function.

Managing how environment variables in the AWS SAM CLI seems a bit convoluted.  I am not the only one with [this opinion](https://github.com/aws/aws-sam-cli/issues/1163)...  As far as I can tell, the _generally_ accepted approach is to define [CloudFormation Parameters](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html).  Then in the function(s) declarations, you set `Environment` to point at these parameters.  Confused yet?

When it comes time for deployment - you can override these parameters to whatever values you want:
`sam deploy --parameter-overrides TileCacheBucket=some-other-bucket`

While this works, it's a bit kludgy when dealing with multiple parameters.  I've adopted a strategy I found in [this issue](https://github.com/aws/aws-sam-cli/issues/2054) - which involves is to creating an .env file at the project root with all CloudFormation Parameters.  And then the deploy command looks like:  `sam deploy --parameter-overrides $(cat .env)`


A final note about the CloudFormation Parameters.  They **MUST** have some value.


#### Enable/Disable S3 Backed Tile Cache
Tile caching has many pros & cons.  For that reason, there is an **_optional_** capability to cache all tiles generated by the Lambda function into a S3 bucket.

In the template.yaml there exists a `TileCacheBucket`.
 - To **enable** tile caching, the value of this parameter should be an existing S3 Bucket name owned by the same AWS account deploying the Lambda function.
 - To **disable** tile caching, set the value of this parameter to a string that is not equal to any S3 Bucket names in the AWS account deploying the Lambda function.  **NOTE:** Per the CloudFormation Parameter spec - there must be a value - so don't attempt to use an empty string here

### Deploying with AWS SAM CLI
The [Admin CLI](#admin-CLI) provides a simple wrapper on top of AWS SAM CLI to deploy:

    admin_cli stack deploy

 Assuming a successful deployment - you should see something like this in your terminal.

    CloudFormation outputs from deployed stack
    -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    Outputs
    -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    Key                 NAIPTileFunction
    Description         NAIPTileFunction Lambda Function ARN
    Value               arn:aws:lambda:us-west-2:109906859411:function:get-naip-tile

    Key                 NAIPLambdaIamRole
    Description         NAIPLambdaRole ARN
    Value               arn:aws:iam::109906859411:role/aws-naip-tile-server-NAIPLambdaRole-1FSITKOVU4EP7

    Key                 DownscaleMaxZoom
    Description         DownscaleMaxZoom
    Value               11

    Key                 UpscaleMinZoom
    Description         UpscaleMinZoom
    Value               19

    Key                 RescalingEnabled
    Description         RescalingEnabled
    Value               TRUE

    Key                 TileCacheBucket
    Description         TileCacheBucket
    Value               aws-naip-tile-server-cache

    Key                 NAIPTileApi
    Description         API Gateway endpoint URL for Prod stage for NAIPTileFunction
    Value               https://1j7kwcy3r0.execute-api.us-west-2.amazonaws.com/prod/tile

    Key                 ImageFormat
    Description         ImageFormat
    Value               JPEG
    -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Of particular importance is the `NAIPTileApi` key.  This is the tile api...

## Usage

### HTTP API

    https://{XYZTileApi.Value}/prod/tile/{year}/{z}/{y}/{x}
	https://1j7kwcy3r0.execute-api.us-west-2.amazonaws.com/prod/tile/2021/11/776/425

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
`admin_cli --help`.

If the poetry shell **isn't** activated - you'll need to use:
`poetry run admin_cli --help`

    Usage: admin_cli [OPTIONS] COMMAND [ARGS]...

      CLI tool to perform admin_cli actions

    Options:
      --help  Show this message and exit.

    Commands:
      cache  Tile Cache related commands.
      stack  AWS CloudFormation related commands.


At the top-level of the API, the commands are really command groups - where each group has 1-M commands for a specific area.  To see the subcommands available for each main command group:
`poetry run admin_cli [@command-group] --help`

Example output for `stack` command group:

    Usage: admin_cli stack [OPTIONS] COMMAND [ARGS]...

      AWS CloudFormation related commands.

    Options:
      --help  Show this message and exit.

    Commands:
      delete  Delete aws-naip-tile-server AWS CloudFormation stack.
      deploy  Deploy aws-naip-tile-server AWS CloudFormation stack.
      status  Display basic info about deployed aws-naip-tile-server AWS...

Then, to get detailed help about a specific command in a command group:
`poetry run admin_cli [@command-group] [@command] --help`

Example output for the `seed` command in the `cache` command-group:

    Usage: admin_cli cache seed [OPTIONS]

      Seed Tile Cache for specific areas/years.

    Options:
      --from_zoom INTEGER  Zoom level caching will start at
      --to_zoom INTEGER    Zoom level caching will end at  [required]
      -y, --years INTEGER  NAIP years to cache
      --coverage TEXT      WKT geometry (WGS84) of ground area to cache tiles for
      --dry-run            Only print summary of how many tiles would be cached
      --help               Show this message and exit.
### Command Groups

#### cache

##### seed
    Usage: admin_cli cache seed [OPTIONS]

      Seed Tile Cache for specific areas/years.

    Options:
      --from_zoom INTEGER  Zoom level caching will start at
      --to_zoom INTEGER    Zoom level caching will end at  [required]
      -y, --years INTEGER  NAIP years to cache
      --coverage TEXT      WKT geometry (WGS84) of ground area to cache tiles for
      --dry-run            Only print summary of how many tiles would be cached
      --help               Show this message and exit.

#### stack

##### delete
    Usage: admin_cli stack delete [OPTIONS]

      Delete aws-naip-tile-server AWS CloudFormation stack.

    Options:
      --help  Show this message and exit.
##### deploy
    Usage: admin_cli stack deploy [OPTIONS]

      Deploy aws-naip-tile-server AWS CloudFormation stack.

    Options:
      --help  Show this message and exit.
##### status
    Usage: admin_cli stack status [OPTIONS]

      Display basic info about deployed aws-naip-tile-server AWS CloudFormation
      stack.

    Options:
      --help  Show this message and exit.

## Known Limitations
### Only using `naip-visualization` bucket
My primary goal was to use NAIP imagery for a basemap, so the `naip-visualization` bucket is most practical for this application.  Currently, there is no way to generate tiles for imagery in the `naip-analytic` or `naip-source` buckets.
### Redundant Tile Creation
It's possible that multiple requests for the same tile could be made at the same time. In the case the tile already exists in the s3 tile cache, there are no issues... But if the tile does not exist in the s3 tile cache, there would be redundant tile creation. The primary issue with redundant tile creation is increased lambda run time, which will cost more $$$. I currently perceive this to be a very minor potential issue... Even implementing some type of lock/wait to prevent redundant tile creation won't decrease lambda run time - because instead of building the tile - the lambda function will be running but idle...
### Degrading Performance for Lower Zoom Levels
As zoom level decreases, the amount of ground area covered by a single tile increases significantly.  Consequently, the number of NAIP geotiffs that need to be accessed to build a tile also increases with decreasing zoom level.  The following table demonstrates this:

| Zoom | Area (approx sq miles) | # NAIP Geotiffs | Tile (xyz)   |
|------|------------------------|-----------------|--------------|
| 14   | 2                      | 2               | 3376,6502,14 |
| 12   | 37                     | 9               | 844,1625,12  |
| 10   | 590                    | 42              | 211,406,10   |
| 8    | 9462                   | 480             | 52,101,8     |

Below zoom level 8, it is likely >1000 NAIP geotiffs need to be accessed to build a single tile, and performance really starts to tank...  In my opinion NAIP does not produce the most appealing basemaps at lower scales for a few reasons.  At this scale, you are likely looking at many different collects, in different states, at different resolutions.  The end result is basemap that is often patchy/blotchy in appearance.  So, I generally don't use NAIP for basemap for low level zooms, therefore it's not travesty that generating tiles < zoom level 8 is slow.


Some Possible Workarounds:
- Set `MinZoomLevel` Parameter to conservative zoom level (Default is 8).  This can be thought of as a 'guard rail' to prevent tile requests that would require accessing 1000+ NAIP geotiffs
- Cache lower zoom levels using the [seed](#seed) command in the [Admin CLI](#admin-cli).
### Spatial Queries on Bundled Parquet File
When a tile is requested, a spatial query is necessary to determine what geotiffs intersect the tile's geometry.  In the current implementation, a parquet index file is bundled in the `src.data` module and used for this purpose.  I chose this approach vs maintaining an index in a separate database of some sort - for simplicity's sake.  I'm fairly confident a spatial query executed against a postgis table would complete quicker than the equivalent parquet query.  So if/when the time comes to chase maximum performance - this is a good place to start...
### Inefficient AWS Lambda Usage
For tiles that are already cached - calling the Lambda function seems inefficient; why not just fetch the tile from S3 directly?  Particularly on cold starts - the extra latency (and Lambda $$$) is avoidable.

## naip-inspector-ui
I've whipped up a no-frills map ui to help debug/asses the tile api.  To start it:
`admin_cli naip-inspector-ui start-dev`

This command is equivalent to:


    cd naip-debugger-ui
    npm install
    npm run dev


The default view will be zoomed out to view CONUS.  Not much is happening (yet) - but you can at least see which states have NAIP coverage by year.  To change years, simply pick another year from the dropdown.
![default](https://github.com/rmferraro/aws-naip-tile-server/assets/4007906/3fb62ea0-30e8-4ff5-bad0-15ac95b7fbb2)


The map has a XYZ tile layer (pointing to the NAIPTileApi) - which its has min & max zooms set to match the Lambda configuration (i.e. template.yaml).  So since my currently configured min zoom = 8, the NAIP tiles won't start loading until I zoom to level 8 or higher.  When the NAIP tiles start loading, you will get a summary of tile loads (per zoom).  You will also see the XYZ tile boundaries with coordinates.
![summary](https://github.com/rmferraro/aws-naip-tile-server/assets/4007906/4ad25766-b067-4f44-ae98-c707547bf2bd)

