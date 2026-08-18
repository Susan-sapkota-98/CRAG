// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: "minor-project-602e3.firebaseapp.com",
  projectId: "minor-project-602e3",
  storageBucket: "minor-project-602e3.firebasestorage.app",
  messagingSenderId: "595217205372",
  appId: "1:595217205372:web:1b6ff258bcbf3bfba861f9"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();