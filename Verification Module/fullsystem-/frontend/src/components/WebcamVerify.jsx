import React, { useRef, useState, useEffect, useCallback } from "react";
import Webcam from "react-webcam";
import API from "../api/api";

export default function WebcamVerify() {

  const webcamRef = useRef(null);

  const [uniqueId, setUniqueId] = useState("");
  const [cameraOn, setCameraOn] = useState(false);

  const [status, setStatus] = useState("");
  const [instruction, setInstruction] = useState("");
  const [progress, setProgress] = useState("");

  const [verified, setVerified] = useState(false);
  const [error, setError] = useState(false);

  const [faceBox, setFaceBox] = useState(null);

  const startVerification = () => {
    if (!uniqueId) return;

    setCameraOn(true);
    setStatus("Align your face inside the frame");
    setInstruction("");
    setProgress("");
    setVerified(false);
    setError(false);
  };

  const sendFrame = useCallback(async () => {

    if (!webcamRef.current || verified || !cameraOn) return;

    const imageSrc = webcamRef.current.getScreenshot();

    if (!imageSrc) return;

    const blob = await fetch(imageSrc).then(res => res.blob());

    const formData = new FormData();

    formData.append("unique_id", uniqueId);
    formData.append("webcam_image", blob);

    try {

      const res = await API.post("/interview/verify-interview", formData);

      const data = res.data;

      console.log("Backend:", data);

      setStatus(data.status || "");
      setInstruction(data.instruction || "");
      setProgress(data.progress || "");

      if (data.face_box) {
        setFaceBox(data.face_box);
      }

      if (data.error) {
        setError(true);
      }

      if (data.verified) {
        setVerified(true);
        setStatus("Verification Successful");
      }

    } catch (err) {

      console.log(err.response?.data);

      setStatus("Server error");
      setError(true);

    }

  }, [cameraOn, verified, uniqueId]);

  useEffect(() => {

    if (!cameraOn || verified) return;

    const interval = setInterval(sendFrame, 800);

    return () => clearInterval(interval);

  }, [cameraOn, verified, sendFrame]);

  return (

    <div style={{ textAlign: "center", fontFamily: "Arial" }}>

      <h2>Live Identity Verification</h2>

      <div style={{ marginBottom: "20px" }}>

        <input
          placeholder="Enter Unique ID"
          value={uniqueId}
          onChange={(e) => setUniqueId(e.target.value)}
          style={{
            padding: "10px",
            fontSize: "16px",
            width: "220px"
          }}
        />

        <button
          onClick={startVerification}
          style={{
            marginLeft: "10px",
            padding: "10px 20px",
            fontSize: "16px",
            cursor: "pointer"
          }}
        >
          Start Verification
        </button>

      </div>

      {cameraOn && (

        <div style={{ position: "relative", width: "500px", margin: "auto" }}>

          <Webcam
            ref={webcamRef}
            screenshotFormat="image/jpeg"
            width={500}
            videoConstraints={{
              facingMode: "user"
            }}
          />

          {faceBox && (

            <div
              style={{
                position: "absolute",
                border: "3px solid lime",
                left: faceBox[0],
                top: faceBox[1],
                width: faceBox[2] - faceBox[0],
                height: faceBox[3] - faceBox[1],
                borderRadius: "10px"
              }}
            />

          )}

        </div>

      )}

      <h3
        style={{
          marginTop: "20px",
          color: verified ? "green" : error ? "red" : "black"
        }}
      >
        {status}
      </h3>

      {instruction && (

        <p style={{ fontSize: "16px" }}>
          {instruction}
        </p>

      )}

      {progress && (

        <p style={{ fontWeight: "bold" }}>
          Step: {progress}
        </p>

      )}

      {verified && (

        <div style={{ marginTop: "20px", color: "green", fontWeight: "bold" }}>
          Identity verified successfully
        </div>

      )}

    </div>

  );

}