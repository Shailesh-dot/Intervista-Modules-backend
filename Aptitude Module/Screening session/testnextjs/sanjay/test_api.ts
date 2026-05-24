async function test() {
  try {
    const response = await fetch("http://localhost:5000/api/submit", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: "Test User",
        email: "test@example.com",
        answers: { q1: "A", q2: "B" }
      }),
    });

    const data = await response.json();
    console.log("Response from server:", data);
  } catch (error) {
    console.error("Error testing API:", error);
  }
}

test();
