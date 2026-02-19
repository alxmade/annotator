/**
 * Sample Express TypeScript file used as a test fixture for annotator.
 */

import express from "express";

const app = express();
const router = express.Router();

function multiply(a: number, b: number): number {
  return a * b;
}

/**
 * Return the sum of two numbers.
 * @param a - First number
 * @param b - Second number
 * @returns Sum
 */
function add(a: number, b: number): number {
  return a + b;
}

app.get("/users", (req, res) => {
  res.json([]);
});

app.post("/users", (req, res) => {
  const { name } = req.body;
  res.json({ name });
});

const getUserById = (id: string) => {
  return { id };
};

router.get("/items", (req, res) => {
  res.json([]);
});

export { multiply, add, getUserById };
