import { Router } from "express";
import { createConversation, getConversations, getMessages, saveMessage, updateConversation } from "../controllers/chat.controller.js";

const chatRouter = Router();

chatRouter.get("/create-conversation", createConversation);
chatRouter.get("/get-conversations", getConversations);
chatRouter.post("/save-message", saveMessage);
chatRouter.get("/get-messages/:conversationId", getMessages);
chatRouter.post("/update-conversation", updateConversation);

export default chatRouter;