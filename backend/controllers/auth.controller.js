import { getAuth } from "firebase-admin/auth";
import { app } from "../config/firebase.js";
import User from "../models/user.model.js";
import { randomUUID } from "crypto";

export const login = async (req, res) => {
    try {
        const { token } = req.body;
        if (!token) {
            return res.status(400).json({ message: "Token missing" });
        }
        const decoded = await getAuth(app).verifyIdToken(token);
        let user = await User.findOne({ firebaseUid: decoded.uid });

        if (!user) {
            user = await User.create({
                firebaseUid: decoded.uid,
                name: decoded.name,
                email: decoded.email,
                avatar: decoded.picture
            });
        }

        const sessionId = randomUUID();
        user.sessionId = sessionId;
        user.sessionExpiresAt = new Date(Date.now() + 1000 * 60 * 60 * 24 * 7);
        await user.save();

        res.cookie("session", sessionId, {
            httpOnly: true,
            secure: false,
            sameSite: "strict",
            maxAge: 1000 * 60 * 60 * 24 * 7 // 7 days
        })



        return res.status(200).json({ message: "Login successful", user });

    } catch (error) {
        return res.status(500).json({ message: "Login failed", error: error.message });
    }
}

export const logout = async (req, res) => {
    try {
        const sessionId = req.cookies?.session;
        if (sessionId) {
            await User.updateOne(
                { sessionId },
                { $set: { sessionId: null, sessionExpiresAt: null } }
            );
        }

        res.clearCookie("session");
        return res.status(200).json({ message: "Logout successful" });
    } catch (error) {
        return res.status(500).json({ message: "Logout failed", error: error.message });
    }
}