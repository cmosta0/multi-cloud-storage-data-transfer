from gcp_functions.main import transfer_from_s3_to_gcs

if __name__ == '__main__':
    transfer_from_s3_to_gcs(prefix='sample_data', given_date='2022/03/19')
