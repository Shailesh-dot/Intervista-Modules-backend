import axios from "axios";

const API = axios.create({
  baseURL: "https://eloise-frizzlier-unradically.ngrok-free.dev",
});

export default API;