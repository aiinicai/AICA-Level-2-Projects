import dotenv from "dotenv";
dotenv.config();

console.log("SMTP_EMAIL:", process.env.SMTP_EMAIL ? `configured (${process.env.SMTP_EMAIL})` : "NOT SET");
console.log("SMTP_APP_PASSWORD:", process.env.SMTP_APP_PASSWORD ? "configured (***)" : "NOT SET");
console.log("SMTP_HOST:", process.env.SMTP_HOST || "default");
console.log("SMTP_PORT:", process.env.SMTP_PORT || "default");
console.log("APP_URL:", process.env.APP_URL || "default");
