const { S3Client, PutObjectCommand, GetObjectCommand } = require("@aws-sdk/client-s3");

const s3 = new S3Client({ region: process.env.AWS_REGION || "us-east-1" });
const S3_BUCKET = process.env.S3_BUCKET || "";

exports.lambdaHandler = async (event) => {
  const action = event.action || "hello";
  const source = event.source || "unknown";

  switch (action) {
    case "hello":
      return hello(source);
    case "s3_write":
      return s3Write(event);
    case "s3_read":
      return s3Read(event);
    default:
      return { statusCode: 400, body: JSON.stringify({ error: `Unknown action: ${action}` }) };
  }
};

function hello(source) {
  return {
    statusCode: 200,
    body: JSON.stringify({
      message: "Hello from Node.js Lambda!",
      source,
      timestamp: new Date().toISOString(),
      runtime: "nodejs20.x",
    }),
  };
}

async function s3Write(event) {
  const key = event.key || `lambda-output/${new Date().toISOString()}.txt`;
  const content = event.content || `Written by Node.js Lambda at ${new Date().toISOString()}`;

  await s3.send(new PutObjectCommand({
    Bucket: S3_BUCKET,
    Key: key,
    Body: content,
  }));

  return {
    statusCode: 200,
    body: JSON.stringify({ message: "Written to S3", bucket: S3_BUCKET, key }),
  };
}

async function s3Read(event) {
  if (!event.key) {
    return { statusCode: 400, body: JSON.stringify({ error: "Missing 'key' in event" }) };
  }

  const response = await s3.send(new GetObjectCommand({
    Bucket: S3_BUCKET,
    Key: event.key,
  }));

  const content = await streamToString(response.Body);
  return {
    statusCode: 200,
    body: JSON.stringify({ bucket: S3_BUCKET, key: event.key, content }),
  };
}

async function streamToString(stream) {
  const chunks = [];
  for await (const chunk of stream) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString("utf-8");
}
