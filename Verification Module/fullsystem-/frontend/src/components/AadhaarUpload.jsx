import { useState } from "react";
import API from "../api/api";

export default function AadhaarUpload({ setUniqueId }) {

  const [file, setFile] = useState(null);
  const [shareCode, setShareCode] = useState("");
  const [msg, setMsg] = useState("");

  const upload = async () => {

    const formData = new FormData();

    formData.append("file", file);
    formData.append("share_code", shareCode);

    try {

      const res = await API.post("/aadhaar/upload", formData);

      console.log("Backend:", res.data);

      setUniqueId(res.data.unique_id);

      setMsg("Aadhaar verified successfully");

    } catch (err) {

      console.log(err.response?.data);

      setMsg(err.response?.data?.detail);
    }
  };

  return (

    <div>

      <h2>Upload Aadhaar ZIP</h2>

      <input
        type="file"
        onChange={(e) => setFile(e.target.files[0])}
      />

      <input
        type="text"
        placeholder="Share Code"
        onChange={(e) => setShareCode(e.target.value)}
      />

      <button onClick={upload}>
        Upload
      </button>

      <p>{msg}</p>

    </div>

  );
}