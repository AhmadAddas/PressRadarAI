import { createServer } from "node:http";

import nodemailer from "nodemailer";

const port = Number.parseInt(process.env.PORT ?? "3001", 10);
export function mailerConfigFrom(environment = process.env) {
  const smtpUser = environment.SMTP_USER ?? "";
  return {
    internalToken: environment.MAILER_INTERNAL_TOKEN ?? "",
    smtpHost: environment.SMTP_HOST?.trim() || "",
    smtpPort: Number.parseInt(environment.SMTP_PORT ?? "587", 10),
    smtpSecure: (environment.SMTP_SECURE ?? "false") === "true",
    smtpUser,
    smtpPassword: environment.SMTP_PASSWORD ?? "",
    smtpFrom: environment.SMTP_FROM?.trim() || smtpUser,
  };
}

const mailerConfig = mailerConfigFrom();
const transporter = nodemailer.createTransport({
  host: mailerConfig.smtpHost,
  port: mailerConfig.smtpPort,
  secure: mailerConfig.smtpSecure,
  requireTLS: true,
  auth: { user: mailerConfig.smtpUser, pass: mailerConfig.smtpPassword },
});

function respond(response, status, body) {
  response.writeHead(status, { "content-type": "application/json" });
  response.end(JSON.stringify(body));
}

async function bodyOf(request) {
  const chunks = [];
  let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > 64 * 1024) throw new Error("request_too_large");
    chunks.push(chunk);
  }
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

export function createMailerServer(
  sendMail = (message) => transporter.sendMail(message),
  config = mailerConfig,
) {
  return createServer(async (request, response) => {
    if (request.method === "GET" && request.url === "/health") {
      respond(response, 200, {
        status: "ok",
        configured: Boolean(
          config.smtpHost && config.smtpUser && config.smtpPassword && config.smtpFrom,
        ),
      });
      return;
    }
    if (request.method !== "POST" || request.url !== "/send") {
      respond(response, 404, { detail: "Not found" });
      return;
    }
    if (
      !config.internalToken ||
      request.headers.authorization !== `Bearer ${config.internalToken}`
    ) {
      respond(response, 401, { detail: "Unauthorized" });
      return;
    }
    if (
      !config.smtpHost ||
      !config.smtpUser ||
      !config.smtpPassword ||
      !config.smtpFrom
    ) {
      respond(response, 503, { detail: "SMTP is not configured" });
      return;
    }
    try {
      const payload = await bodyOf(request);
      if (
        typeof payload.to !== "string" ||
        typeof payload.subject !== "string" ||
        typeof payload.text !== "string" ||
        (payload.message_id !== null &&
          payload.message_id !== undefined &&
          (typeof payload.message_id !== "string" ||
            !/^[A-Za-z0-9@._-]{1,200}$/.test(payload.message_id))) ||
        !payload.to ||
        !payload.subject ||
        !payload.text ||
        payload.to.length > 320 ||
        payload.subject.length > 200 ||
        payload.text.length > 10_000 ||
        /[\r\n]/.test(payload.to) ||
        /[\r\n]/.test(payload.subject)
      ) {
        respond(response, 422, { detail: "Invalid email payload" });
        return;
      }
      const message = {
        from: config.smtpFrom,
        to: payload.to,
        subject: payload.subject,
        text: payload.text,
      };
      if (payload.message_id) message.messageId = payload.message_id;
      const result = await sendMail(message);
      respond(response, 202, { message_id: result.messageId });
    } catch (error) {
      const status = error instanceof SyntaxError ? 400 : 502;
      respond(response, status, { detail: "Email delivery failed" });
    }
  });
}

if (process.env.NODE_ENV !== "test") {
  createMailerServer().listen(port, "0.0.0.0");
}
