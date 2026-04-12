import { initializeApp, getApps } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyAVGKX7dptTOyknC6LW9XK-Deve-wkbOLQ",
  authDomain: "chickfinder-ac09d.firebaseapp.com",
  projectId: "chickfinder-ac09d",
  storageBucket: "chickfinder-ac09d.firebasestorage.app",
  messagingSenderId: "1057586845754",
  appId: "1:1057586845754:web:1c991c621820292c2b3d03",
  measurementId: "G-7DWN267JVN",
};

const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
export const auth = getAuth(app);
export default app;
