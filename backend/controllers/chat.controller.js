import Conversation from "../models/conversation.model.js";
import Message from "../models/message.model.js";

export const createConversation = async (req, res) => {
    try {
        const userId = req.headers['x-user-id'];
        console.log("User ID from header:", userId);
        if (!userId) {
            return res.status(400).json({ message: "User ID missing in headers" });
        }
        const conversation = await Conversation.create({ userId });
        return res.status(201).json({ message: "Conversation created", conversation });
    } catch (error) {
        return res.status(500).json({ message: "Failed to create conversation", error: error.message });
    }   
}

export const getConversations = async (req, res) => {
    try {
        const userId = req.headers['x-user-id'];
        if (!userId) {
            return res.status(400).json({ message: "User ID missing in headers" });
        }
        const conversations = await Conversation.ind({ userId }).sort({ updatedAt: -1 });
        return res.status(200).json({ message: "Conversations fetched", conversations });
    } catch (error) {
        return res.status(500).json({ message: "Failed to fetch conversations", error: error.message });
    }
}

export const saveMessage = async (req, res) => {
    try {
        const { conversationId, role, content } = req.body;
        const userId = req.headers['x-user-id'];
        if (!conversationId || !content) {
            return res.status(400).json({ message: "conversationId and content are required" });
        }
        const message = await Message.create({
            conversationId,
            role,
            content
        });

        return res.status(201).json({ message: "Message saved", message });
    } catch (error) {
        return res.status(500).json({ message: "Failed to save message", error: error.message });
    }
}

export const getMessages = async (req, res) => {
    try {
        const { conversationId } = req.params;
        if (!conversationId) {
            return res.status(400).json({ message: "conversationID missing" });
        }
        const messages = await Message.find({ conversationId }).sort({ createdAt: -1 });
        return res.status(200).json({ message: "Messages fetched", messages });
    } catch (error) {
        return res.status(500).json({ message: "Failed to fetch messages", error: error.message });
    }
}

export const updateConversation= async (req, res) => {
    try {
        const { id, title } = req.body;
        if (!id || !title) {    
            return res.status(400).json({ message: "conversationId and title are required" });
        }           
        const conversation = await Conversation.findByIdAndUpdate(id, { title });        
        if (!conversation) {
            return res.status(404).json({ message: "Conversation not found" });
        }
        return res.status(200).json({ message: "Conversation updated", conversation });
    } catch (error) {
        return res.status(500).json({ message: "Failed to update conversation", error: error.message });
    }
}
        