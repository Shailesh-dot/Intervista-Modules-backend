import { useState } from "react";
import API from "../api/api";

export default function FaceVerify({ setNext }) {

  const [uniqueId, setUniqueId] = useState("");
  const [maskedAadhaar, setMaskedAadhaar] = useState("");
  const [photo, setPhoto] = useState(null);
  const [msg, setMsg] = useState("");

  const verify = async () => {

    const formData = new FormData();

    formData.append("unique_id", uniqueId);
    formData.append("masked_aadhaar", maskedAadhaar);
    formData.append("photo", photo);

    try {

      const res = await API.post("/face/verify", formData);

      console.log("Backend:", res.data);

      setMsg("Face verified");

      setNext(true);

    } catch (err) {

      console.log(err.response?.data);

      setMsg(err.response?.data?.detail);
    }
  };

  return (

    <div>

      <h2>Face Verification</h2>

      <input
        placeholder="Unique ID"
        onChange={(e) => setUniqueId(e.target.value)}
      />

      <input
        placeholder="Last 4 Aadhaar"
        onChange={(e) => setMaskedAadhaar(e.target.value)}
      />

      <input
        type="file"
        onChange={(e) => setPhoto(e.target.files[0])}
      />

      <button onClick={verify}>
        Verify Face
      </button>

      <p>{msg}</p>

    </div>

  );
}