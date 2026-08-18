import { signInWithPopup } from "firebase/auth"
import api from "../utils/axios"
import HomePage from "./pages/HomePage"
import { useEffect } from "react"
import getCurrentUser from "./features/getCurrentUser"
import { useDispatch } from "react-redux"
import { setUserData } from "./redux/userSlice"

function App() {
    const dispatch = useDispatch();
    useEffect(() => {
        const getUser = async () => {
            const data = await getCurrentUser();
            dispatch(setUserData(data));
        }
        getUser();
    }, []);

    return (
        <HomePage />
    )
}

export default App