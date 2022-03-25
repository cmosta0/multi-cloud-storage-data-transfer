# Multi cloud data transfer - POC

## Summary

Create a `GCP` solution for a data transfer with `AWS-s3` as source data dn `GCS` as destination.

## Use case scenario

`AWS-s3` as third-party service, with only keys for `AWS-authentication` without access to any other service and/or permission.
Data is going to be partitioned in folders based on a given date and prefix with the following format:

`s3://<BUCKET_NAME>/<prefix>/<YYYY>/<MM>/<DD>/[{file_names}.json]*`

Our goal is create a solution to transfer data from `aws` to `gcs`. Our solution should be flexible to use it for
a custom backfill and an automated job which is responsible to ingest given the execution date the corresponding data.

Given above conditions, services like `data-transfer` which would do this job with only 2-3 clicks, is not an option since
that requires specific permissions on the source buckets from where we have only read access to the objects and list permission
to the specific bucket.

## Solution overview

Our solution will be based on 3 GCP services:

- `cloud-function`: Core for the data transfer. Given the parameters, our function will be responsible to transfer our data
from `aws-s3` to `gcs`.
- `Pub/Sub`: With this service we'll trigger our `cloud-function`.
- `Cloud scheduler`: Using `cloud-scheduler` we'll schedule publishing a message to `Pub/Sub` with the specific params to either 
execute a fixed-date for the partitioned data-folders or determine that date given the execution datetime when this process
is executed.

## Solution in action...

### Prerequisites

- AWS account
- GCP account

### Preparation steps

- Create a bucket on `AWS`
- Create an `IAM` `service-user` on `AWS`
- Create a bucket on `GCS`

### Sample source data for POC

There is some sample data located on `utils/sample_data`, with a date-format folders that you can use for this POC.
Also, you can create your custom data following specified format and place the data you want to transfer.

### Upload of source data

Once you've created your `AWS-S3` `bucket`, upload your source data folder at the top of it.

Example, if you're going to use `utils/sample_data`, upload the `sample_data` folder directly and not only the child-folders.
So that, our source data will look like:

`s3://<MY_BUCKET>/sample_data/[date folders]`

## GCP Services creation

We'll follow create our GCP services in the below order:

1. `Pub/Sub` 
2. `Secret`
3. `Cloud Function`
4. `Cloud Scheduler`

Below steps will illustrate the programmatic way for services creation, however, you can do the same directly from UI.

### Gcloud-cli setup

Before start creating the services, we need to setup our gcp-cli client in order to connect with our `gcp-account`.

Installation and setup: <https://cloud.google.com/sdk/gcloud>

### Environment variables

```shell
export AWS_SERVICE_ACCESS_KEY="<YOUR_AWS_SERVICE_ACCESS_KEY>"
export AWS_SERVICE_SECRET="<YOUR_AWS_SERVICE_SECRET>"
export AWS_REGION="<YOUR_AWS_REGION>"
export GCP_PROJECT_NAME="<YOUR_GCP_PROJECT_NAME>"
export S3_BUCKET="<YOUR_S3_BUCKET>"
export GCS_BUCKET="<YOUR_GCS_BUCKET>"
```

## Pub/Sub topic creation

Let's create our `topic` on `Pub/Sub` by running below command:

```shell
gcloud pubsub topics create data-transfer-topic
```


## Secrets creation

Depending on the data we can either send it on the message and receive it on the `cloud-function` like
the arguments on the call or set it as environment variable.

However, there is some kind of data (sensitive data), like passwords, keys, etc that we should not send 
as plain text. For these cases we can use `secrets` to define it and use directly as environment variable 
from the `cloud-function` code.

In our case, we'll set a couple of secrets to store our aws authentication keys.

Once we have our environment variables defined, we can run below commands which are going to create our secrets:

```shell
echo $AWS_SERVICE_ACCESS_KEY | gcloud secrets create data-transfer-aws-access-key --data-file=- 
echo $AWS_SERVICE_SECRET | gcloud secrets create data-transfer-aws-secret-key --data-file=- 
```

## Cloud function creation

Now, we'll use our `Pub/Sub` `topic` and secret to create the `cloud-function` with the below command:

```shell
gcloud functions deploy dataTransferS3GcsFunction \
  --runtime=python39 \
  --source=gcp_functions \
  --entry-point=data_transfer_handler \
  --trigger-topic=data-transfer-topic \
  --set-secrets=AWS_SERVICE_ACCESS_KEY=data-transfer-aws-access-key:latest,AWS_SERVICE_SECRET=data-transfer-aws-secret-key:latest \
  --update-env-vars S3_BUCKET=$S3_BUCKET,GCS_BUCKET=$GCS_BUCKET,GCP_PROJECT_NAME=$GCP_PROJECT_NAME,AWS_REGION=$AWS_REGION
  ```

Note: Since we're going to user `secrets` on our `cloud-function`, we need to grant access this access to the `service-account`  
that will trigger our function.

Go to: <https://console.cloud.google.com/iam-admin/iam>, look for your service account and add this permission: `Secret Manager Secret Accessor`

## Cloud scheduler creation

Let's create the final component for our solution. To create the `cloud scheduler`, let's run below command: 

````shell
 gcloud scheduler jobs create pubsub dataTransferCronTrigger --location=us-east1 \
        --schedule "*/10 * * * *" \
        --topic data-transfer-topic \
        --attributes DATA_PREFIX=sample_data \
        --time-zone UTC
````

_Notes_: 
- This example defines a scheduled job to be executed every 10 min, you can customize it. If you're not familiar with cron's, you can use: <https://crontab.guru/>
- Take in mind that not all locations are available for cloud functions. Take a look into: <https://cloud.google.com/functions/docs/locations>.


## Verification

At this point, our cloud scheduler should send a message to the `Pub/Sub` `topic` and since the `cloud-function` is subscribed to it, it will be triggered, reading 
the attribute which specify the prefix (subfolder inside the bucket) and date-folder, for the poc we set it as `None` which means it will 
calculate it based on the execution date. It's important that the input data have the current input date, otherwise it wont transfer anything.

