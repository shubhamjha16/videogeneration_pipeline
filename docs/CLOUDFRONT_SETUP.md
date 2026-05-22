# AWS CloudFront CDN Setup & CORS Policy Guide

This guide documents how to configure **AWS CloudFront** in front of your production S3 bucket (`easetolearn-video-assets`) to ensure fast, low-latency video streaming to students, eliminate direct S3 egress costs, and secure assets from unauthorized hotlinking.

---

## 1. Secure Bucket Access: Origin Access Control (OAC)
To prevent users from bypassing your CDN and accessing S3 URLs directly (which inflates hosting costs), restrict S3 access strictly to CloudFront using **Origin Access Control (OAC)**.

### Step-by-Step AWS Console Configuration:
1. Open the **CloudFront Console** and click **Create Distribution**.
2. **Origin Domain**: Select your S3 bucket (e.g., `easetolearn-video-assets.s3.ap-south-1.amazonaws.com`).
3. **Origin Access**: Choose **Origin access control settings (recommended)**.
4. Click **Create control setting**, name it `easetolearn-s3-oac`, set signing behavior to **Sign requests (recommended)**, and click **Create**.
5. Scroll down to **Default Cache Behavior**:
   * **Viewer Protocol Policy**: Select **Redirect HTTP to HTTPS**.
   * **Allowed HTTP Methods**: Select `GET, HEAD, OPTIONS` (crucial for video players performing byte-range requests).
6. Under **Cache Key and Origin Requests**:
   * Select **Cache policy**: `CachingOptimized`.
   * Select **Origin request policy**: `CORS-S3Origin` (crucial to forward CORS headers to S3).
7. Click **Create Distribution**.
8. **CRITICAL STEP**: Once created, CloudFront will display a banner: *"The S3 bucket policy needs to be updated..."*. Copy the generated bucket policy and proceed to your S3 console.

---

## 2. Apply S3 Bucket Policy
Paste the copied policy into your S3 bucket's **Permissions** tab. It will look like this:

```json
{
    "Version": "2012-10-17",
    "Statement": {
        "Sid": "AllowCloudFrontServicePrincipalReadOnly",
        "Effect": "Allow",
        "Principal": {
            "Service": "cloudfront.amazonaws.com"
        },
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::easetolearn-video-assets/videos/*",
        "Condition": {
            "ArnEquals": {
                "AWS:SourceArn": "arn:aws:cloudfront::<your-aws-account-id>:distribution/<your-cloudfront-distribution-id>"
            }
        }
    }
}
```

---

## 3. Enable CORS on S3 Bucket
HTML5 video players (like Video.js or Plyr) make `GET` requests with `Range` headers to buffer videos. If CORS is not enabled on S3, the browser will block the stream.

Paste this **CORS Configuration** under the S3 bucket's **CORS** section:

```json
[
    {
        "AllowedHeaders": [
            "*"
        ],
        "AllowedMethods": [
            "GET",
            "HEAD"
        ],
        "AllowedOrigins": [
            "https://easetolearn.com",
            "https://portal.easetolearn.com",
            "http://localhost:3000"
        ],
        "ExposeHeaders": [
            "ETag",
            "Content-Type",
            "Accept-Ranges",
            "Content-Length",
            "Content-Range"
        ],
        "MaxAgeSeconds": 3000
    }
]
```

---

## 4. Mapping S3 to CloudFront in Spring Boot

In your Spring Boot `Tony AI` code, once you receive the `video_url` from the factory (which references the raw S3 bucket URL, e.g., `https://easetolearn-video-assets.s3.ap-south-1.amazonaws.com/videos/abc.mp4`), transform it to your CloudFront public CDN URL before serving it to the frontend:

```java
public class CDNUrlMapper {
    private static final String S3_DOMAIN = "easetolearn-video-assets.s3.ap-south-1.amazonaws.com";
    private static final String CLOUDFRONT_DOMAIN = "https://d12345abcdef.cloudfront.net"; // Replace with your actual CF Domain

    public static String convertToCDNUrl(String s3Url) {
        if (s3Url == null || !s3Url.contains(S3_DOMAIN)) {
            return s3Url;
        }
        return s3Url.replace("https://" + S3_DOMAIN, CLOUDFRONT_DOMAIN);
    }
}
```
