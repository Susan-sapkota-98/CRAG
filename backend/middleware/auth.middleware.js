import User from "../models/user.model.js";

const protect = async (req, res, next) => {
    try {
        const sessionId = req.cookies?.session
        if(!sessionId) {
            return res.status(401).json({ message: "Unauthorized" })
        }
        const user = await User.findOne({
            sessionId,
            sessionExpiresAt: { $gt: new Date() }
        }).select("_id name email avatar");

        if(!user) {
            return res.status(401).json({ message: "session expired" })
        }

        req.user = {
            userId: user._id,
            name: user.name,
            email: user.email,
            avatar: user.avatar
        }

        next()
    } catch (error) {   
        return res.status(500).json({ message: "Internal Server Error" })
    }
}

export default protect;