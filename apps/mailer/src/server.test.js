import assert from "node:assert/strict";
import { afterEach, test } from "node:test";

process.env.NODE_ENV = "test";
process.env.MAILER_INTERNAL_TOKEN = "test-token";
process.env.SMTP_USER = "sender@example.com";
process.env.SMTP_PASSWORD = "app-password";

const { createMailerServer, mailerConfigFrom } = await import("./server.js");
let server;
const config = {
  internalToken: "test-token",
  smtpHost: "smtp.example.com",
  smtpPort: 587,
  smtpSecure: false,
  smtpUser: "sender@example.com",
  smtpPassword: "app-password",
  smtpFrom: "sender@example.com",
};

afterEach(() => server?.close());

test("uses the SMTP user when Compose supplies a blank sender", () => {
  const resolved = mailerConfigFrom({
    MAILER_INTERNAL_TOKEN: "test-token",
    SMTP_USER: "sender@example.com",
    SMTP_PASSWORD: "app-password",
    SMTP_FROM: "",
  });

  assert.equal(resolved.smtpFrom, "sender@example.com");
});

test("sends an authorized email without exposing SMTP credentials", async () => {
  let delivered;
  server = createMailerServer(async (message) => {
    delivered = message;
    return { messageId: "message-1" };
  }, config);
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();

  const response = await fetch(`http://127.0.0.1:${port}/send`, {
    method: "POST",
    headers: {
      authorization: "Bearer test-token",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      to: "recipient@example.com",
      subject: "PressRadar verification code",
      text: "Your code is 123456",
    }),
  });

  assert.equal(response.status, 202);
  assert.deepEqual(delivered, {
    from: "sender@example.com",
    to: "recipient@example.com",
    subject: "PressRadar verification code",
    text: "Your code is 123456",
  });
});

test("rejects callers without the internal bearer token", async () => {
  server = createMailerServer(async () => ({ messageId: "unexpected" }), config);
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();

  const response = await fetch(`http://127.0.0.1:${port}/send`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ to: "a@example.com", subject: "Subject", text: "Body" }),
  });

  assert.equal(response.status, 401);
});

test("rejects newline injection in email headers", async () => {
  server = createMailerServer(async () => ({ messageId: "unexpected" }), config);
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();

  const response = await fetch(`http://127.0.0.1:${port}/send`, {
    method: "POST",
    headers: {
      authorization: "Bearer test-token",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      to: "recipient@example.com\r\nBcc: attacker@example.com",
      subject: "Subject",
      text: "Body",
    }),
  });

  assert.equal(response.status, 422);
});

test("forwards a stable message id for idempotent pitch retries", async () => {
  let delivered;
  server = createMailerServer(async (message) => {
    delivered = message;
    return { messageId: message.messageId };
  }, config);
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();

  const response = await fetch(`http://127.0.0.1:${port}/send`, {
    method: "POST",
    headers: {
      authorization: "Bearer test-token",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      to: "recipient@example.com",
      subject: "PressRadar pitch",
      text: "Pitch body",
      message_id: "pressradar-opportunity-1@delivery.local",
    }),
  });

  assert.equal(response.status, 202);
  assert.equal(delivered.messageId, "pressradar-opportunity-1@delivery.local");
});
