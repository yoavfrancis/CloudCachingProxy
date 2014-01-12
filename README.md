Cloud Caching Proxy
=================

A scalable caching proxy based on Amazon Web Services

### Setup notes : 

The "files_to_upload" folder contains the files required for the proxy AMI creation and is not to be modified.

In order to create the cloud orchestration, run the setup() function from setup.py.
After the orchestration is finished you'll be displayed with the proxy public address (it runs on port 8080) - this is the address of the load balancer that sits behind the auto-scaled EC2 instances.

In order to tear-down, run the clean_all() function form setup.py

Specific configuration (keys, region) should be made in the config.py file.
Other files should be left intact.

### Project Presentation
A PPT describing the project is available [here](http://www.slideshare.net/YoavFrancis/cloud-caching-proxy-scalable)

### Author

Joint work by [Yoav Francis](https://www.linkedin.com/in/yoavfrancis) and Tomer Cagan for Cloud Computing Course, IDC Herzelia 2013
