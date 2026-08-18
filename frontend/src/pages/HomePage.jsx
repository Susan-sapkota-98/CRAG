import { signInWithPopup } from "firebase/auth"
import { auth, googleProvider } from "../../utils/firebase"
import api from "../../utils/axios"
import { FcGoogle } from "react-icons/fc";
import { useDispatch, useSelector } from "react-redux";
import { setUserData } from "../redux/userSlice";
import Artifact from "../components/Artifact";
import SideBar from "../components/SideBar";
import ChatArea from "../components/ChatArea";

function HomePage() {
    const { userData } = useSelector((state) => state.user);
    const dispatch = useDispatch();

    console.log("User data from Redux store:", userData);
    const handleGoogleLogIn = async (token) => {
        try {
            const { data } = await api.post("/api/auth/login", { token })
            dispatch(setUserData(data));
        } catch (error) {
            console.error("Error during Google login:", error)
        }
    }

    const handleGoogleSignIn = async () => {
        const data = await signInWithPopup(auth, googleProvider)
        const token = await data.user.getIdToken()
        await handleGoogleLogIn(token)
    }

    return (
        <div className="h-screen flex bg-[#0d0f14] text-white overflow-hidden">

            <SideBar />
            <ChatArea />
            <Artifact />

            {!userData && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur">
                <div className="w-85 bg-[#13151c] border border-white/8 rounded-2xl p-7 flex flex-col gap-5">
                    <div>
                        <h2 className="text-[17px] font-semibold text-slate-100 tracking-tight">Welcome to MultiQA.AI</h2>
                        <p className="text-[13px] text-slate-500">Please login to continue using the app.</p>
                    </div>

                    <button className="w-full flex items-center justify-center gap-3 py-2.75 rounded-xl text-sm font-medium text-white bg-linear-to-br from-indigo-500 to-violet-700 hover:from-indigo-400 hover-to-violet-600 active:from-indigo-600 active:to-violet-800 border border-indigo-500/30 shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/30 transition-all duration-150 cursor-pointer" onClick={handleGoogleSignIn}>
                        <FcGoogle size={15} className="text-white" />
                        Continue with Google
                    </button>

                </div>
            </div>}

        </div>
    )
}

export default HomePage