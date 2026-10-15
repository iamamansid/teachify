/**
 * Teachify MCP server (stdio).
 *
 * Turns any MCP-capable LLM (Claude Code, Cursor, Codex, VS Code) into a
 * teacher, not a doer. The server NEVER writes code for the learner and
 * NEVER returns a full solution. It guides, verifies, hints, and quizzes.
 *
 * Run:  node dist/server.js
 * Config (.mcp.json): { "mcpServers": { "teachify": { "command": "node", "args": ["/absolute/path/to/teachify/dist/server.js"] } } }
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { getHint } from "./engine/hints.js";
import { buildDynamicTask, validateTeachPlan } from "./engine/plan.js";
import {
  advanceSession,
  createSession,
  createSessionForTask,
  currentStep,
  getSession,
  getTaskForSession,
  isComplete,
  recordAttempt,
  toPublicStep,
} from "./engine/session.js";
import { getTask, listTaskSummaries, loadTasks, registerDynamicTask } from "./engine/tasks.js";
import { getTeachModePrompt, TEACH_MODE_EXAMPLE_PROMPT, TEACH_MODE_HOW_TO_USE, TEACH_MODE_RULES } from "./engine/teach-mode.js";
import { verifyStep } from "./engine/verifier.js";

const VERSION = "0.1.0";

const CONCEPTS: Record<string, { explanation: string; analogy: string; tryIt: string }> = {
  "rest": {
    explanation:
      "REST is a style for web APIs: resources (like /hello) are addressed by URLs, and HTTP verbs (GET, POST, PUT, DELETE) say what to do with them. GET should only read, never change data.",
    analogy: "Like a library: the URL is the shelf address, GET is 'let me read this book', POST is 'add a new book'.",
    tryIt: "In your own words, explain why GET /hello should not create a user. Then name one POST endpoint you would add to a todo API.",
  },
  "express": {
    explanation:
      "Express is a minimal Node.js web framework. You create an app with express(), register routes with app.get()/app.post(), and start listening with app.listen(). Each route maps a URL + verb to a handler (req, res).",
    analogy: "Like a reception desk: routes are the directory board — 'GET /hello → talk to this person'.",
    tryIt: "Without looking at your code: what does app.listen() do, and what happens if you forget it?",
  },
  "spring-boot": {
    explanation:
      "Spring Boot is an opinionated Java framework that wires up a web server, dependency injection, and routing for you. @RestController marks a class as a web controller; @GetMapping binds a method to HTTP GET on a path.",
    analogy: "Like a restaurant: @RestController is the kitchen, @GetMapping is the menu — 'GET /hello → this dish'.",
    tryIt: "Explain in one sentence what happens when a request hits GET /hello in your Spring app, from annotation to response.",
  },
  "annotation": {
    explanation:
      "An annotation (like @RestController) is metadata on a class or method. The framework reads it at startup and changes behaviour — e.g. registering the class as a controller — without you writing boilerplate.",
    analogy: "Like a sticky note on a box: 'fragile — handle as a controller'. The handler (Spring) reads the note.",
    tryIt: "Name two Spring annotations you used and what each one caused Spring to do.",
  },
  "middleware": {
    explanation:
      "Middleware is a function that runs between receiving a request and sending a response — e.g. logging, auth, JSON parsing. In Express you register it with app.use(). It can inspect, modify, or short-circuit the request.",
    analogy: "Like airport security between check-in and the gate: every passenger passes through, some get stopped.",
    tryIt: "Design (in words, no code) a middleware that logs the method + path of every request. Where would you register it?",
  },
  "dependency-injection": {
    explanation:
      "Dependency injection means a class receives its collaborators (e.g. a service) from the framework instead of creating them with `new`. Spring constructs and wires beans; your class just declares what it needs.",
    analogy: "Like a chef who is handed prepped ingredients instead of growing them. The kitchen (Spring) supplies them.",
    tryIt: "In your controller, what would you inject if the greeting came from a service? Sketch the constructor in words.",
  },
  "closure": {
    explanation:
      "A closure is a function that remembers variables from the scope where it was created, even after that scope has finished. In JS, the handler (req, res) => { ... } closes over variables like `app` if it references them.",
    analogy: "Like a backpack: the function carries the variables it needs from home.",
    tryIt: "Write (by hand) a tiny function that returns a counter function. Predict what each call returns before you run it.",
  },
  "async": {
    explanation:
      "Async code lets Node handle other requests while waiting for slow work (DB, network). async/await is syntax over Promises: await pauses that function until the Promise resolves, without blocking the whole server.",
    analogy: "Like ordering food: you get a buzzer (Promise) and sit down; the kitchen buzzes you when it is ready.",
    tryIt: "Explain why blocking the event loop with a long sync loop would freeze ALL requests, not just yours.",
  },
};

function text(obj: unknown) {
  return { content: [{ type: "text" as const, text: JSON.stringify(obj, null, 2) }] };
}

function explainConcept(concept: string, context?: string) {
  const key = concept.toLowerCase().trim();
  const hit =
    CONCEPTS[key] ??
    Object.entries(CONCEPTS).find(([k]) => key.includes(k) || k.includes(key))?.[1];
  if (hit) {
    return {
      concept,
      explanation: hit.explanation,
      analogy: hit.analogy,
      tryItYourself: hit.tryIt,
      ...(context ? { context } : {}),
      note: "Teachify explains — it does not write the code for you.",
    };
  }
  return {
    concept,
    explanation:
      `I do not have a canned lesson for "${concept}" yet. Here is the teaching pattern: ` +
      `state the definition in one sentence, name the smallest example, then try it yourself. ` +
      `Ask me to break "${concept}" into a 3-step task and I will build the steps (you still type the code).`,
    analogy: "Like learning to ride a bike: you need the balance idea + one small practice loop, not a lecture.",
    tryItYourself: `In your own words, define "${concept}" in one sentence, then give one concrete example from code you have written.`,
    ...(context ? { context } : {}),
    note: "Teachify explains — it does not write the code for you.",
  };
}

export function createServer(): McpServer {
  const server = new McpServer({ name: "teachify", version: VERSION });

  server.tool(
    "teach_start_task",
    "Start a guided learning task. Returns the task overview + step 1 only — never the full solution. The learner types every line.",
    {
      taskId: z.string().describe("Task id, e.g. js-express-hello or java-spring-hello"),
      mode: z.enum(["teach", "hint", "do"]).optional().default("teach").describe(
        "teach = guide only, never types code. hint = nudge-first. do = only on explicit request, does boilerplate then quizzes you."
      ),
    },
    async ({ taskId, mode }) => {
      const task = getTask(taskId);
      if (!task) {
        return text({
          error: `Unknown taskId "${taskId}".`,
          availableTasks: listTaskSummaries(),
        });
      }
      const session = createSession(taskId, mode ?? "teach");
      return text({
        sessionId: session.id,
        mode: session.mode,
        task: {
          id: task.id,
          title: task.title,
          description: task.description,
          level: task.level,
          estimatedMinutes: task.estimatedMinutes,
          totalSteps: task.steps.length,
          learningOutcomes: task.learningOutcomes,
        },
        currentStep: toPublicStep(task, 0),
        rule: "The learner types every line. Teachify guides, verifies, hints, and quizzes — it never writes the solution.",
        next: "Call teach_check_step with { sessionId, file, content } after the learner completes this step.",
      });
    }
  );

  server.tool(
    "teach_next_step",
    "Return the current step. If the previous step is not yet verified, returns it again with a reminder — it never skips ahead or reveals the next solution.",
    { sessionId: z.string() },
    async ({ sessionId }) => {
      const session = getSession(sessionId);
      if (!session) return text({ error: `Unknown sessionId "${sessionId}". Start with teach_start_task.` });
      const task = getTaskForSession(session);
      if (isComplete(session)) {
        return text({
          done: true,
          message: "Task complete — every step verified. Call teach_quiz to check understanding, then teach_progress for a summary.",
          stepsCompleted: session.stepsCompleted.length,
          totalSteps: task.steps.length,
        });
      }
      return text({
        sessionId: session.id,
        currentStep: toPublicStep(task, session.currentStepIndex),
        reminder: "Complete this step first, then call teach_check_step. Teachify will not advance on an unverified step.",
      });
    }
  );

  server.tool(
    "teach_check_step",
    "Verify the learner's current step from file content or file path. Returns pass/fail + targeted feedback. On fail, never reveals the next solution.",
    {
      sessionId: z.string(),
      file: z.string().optional().describe("Relative file path, e.g. server.js. If omitted, the step's file is used."),
      content: z.string().optional().describe("File text to verify. If omitted, Teachify reads the file from disk."),
    },
    async ({ sessionId, file, content }) => {
      const session = getSession(sessionId);
      if (!session) return text({ error: `Unknown sessionId "${sessionId}". Start with teach_start_task.` });
      const task = getTaskForSession(session);
      if (isComplete(session)) {
        return text({ done: true, message: "Task already complete. Call teach_quiz or teach_progress." });
      }
      const step = currentStep(session);
      recordAttempt(session, step.id);
      const result = verifyStep(step, { content, file: file ?? step.file });
      if (!result.pass) {
        if (session.attempts[step.id] >= 3) {
          session.masteryNotes.push(`Needed ${session.attempts[step.id]} attempts on "${step.title}" — revisit this concept.`);
        }
        return text({
          pass: false,
          stepId: step.id,
          stepTitle: step.title,
          feedback: result.feedback,
          attempts: session.attempts[step.id],
          suggestion: "Stuck? Call teach_hint with level 1, then 2, then 3. Hints escalate but never type the code for you.",
        });
      }
      advanceSession(session);
      const done = isComplete(session);
      return text({
        pass: true,
        stepId: step.id,
        stepTitle: step.title,
        feedback: `Nice — "${step.title}" verified. ${done ? "Task complete!" : "Moving to the next step."}`,
        progress: { completed: session.stepsCompleted.length, total: task.steps.length },
        ...(done
          ? { next: "Call teach_quiz to check understanding." }
          : {
              nextStepPreview: {
                stepNumber: session.currentStepIndex + 1,
                title: task.steps[session.currentStepIndex].title,
              },
              note: "Full instructions for the next step come from teach_next_step — the preview above is title-only by design.",
            }),
      });
    }
  );

  server.tool(
    "teach_hint",
    "Escalating hints for the current step. Level 1 = nudge, 2 = shape of the code, 3 = strongest hint. Level 3 still does NOT type the code for the learner.",
    {
      sessionId: z.string(),
      level: z.union([z.literal(1), z.literal(2), z.literal(3)]).optional().default(1),
    },
    async ({ sessionId, level }) => {
      const session = getSession(sessionId);
      if (!session) return text({ error: `Unknown sessionId "${sessionId}".` });
      const task = getTaskForSession(session);
      if (isComplete(session)) return text({ done: true, message: "Task complete — no hints needed. Try teach_quiz." });
      const step = currentStep(session);
      session.hintsUsed += 1;
      return text({
        stepId: step.id,
        stepTitle: step.title,
        level,
        hint: getHint(step, level as 1 | 2 | 3),
        rule: "Hints guide — you still type the code.",
      });
    }
  );

  server.tool(
    "teach_quiz",
    "Return 2-3 questions about what the learner just did. Questions include options; answerIndex + explanation are for LLM grading ONLY — the LLM must ask the learner first and not reveal answers upfront.",
    { sessionId: z.string() },
    async ({ sessionId }) => {
      const session = getSession(sessionId);
      if (!session) return text({ error: `Unknown sessionId "${sessionId}".` });
      const task = getTaskForSession(session);
      return text({
        sessionId: session.id,
        taskTitle: task.title,
        progress: { completed: session.stepsCompleted.length, total: task.steps.length },
        questions: task.quiz,
        gradingInstruction:
          "Ask the learner each question WITHOUT showing answerIndex/explanation. Grade their answer, then share the explanation. If they miss one, point them back to the step that taught it.",
      });
    }
  );

  server.tool(
    "teach_explain",
    "Short explanation of a concept + analogy + a try-it-yourself prompt. Explains, never writes the learner's code.",
    {
      concept: z.string().describe("Concept to explain, e.g. REST, middleware, annotation, closure"),
      context: z.string().optional().describe("Optional context, e.g. the task the learner is on"),
    },
    async ({ concept, context }) => text(explainConcept(concept, context))
  );

  server.tool(
    "teach_progress",
    "Progress summary for a session: steps done, time spent, attempts, hints, mastery notes.",
    { sessionId: z.string() },
    async ({ sessionId }) => {
      const session = getSession(sessionId);
      if (!session) return text({ error: `Unknown sessionId "${sessionId}".` });
      const task = getTaskForSession(session);
      const elapsedMin = Math.round((Date.now() - session.startedAt) / 60000);
      return text({
        sessionId: session.id,
        task: { id: task.id, title: task.title },
        mode: session.mode,
        progress: {
          completed: session.stepsCompleted.length,
          total: task.steps.length,
          stepsCompleted: session.stepsCompleted,
          currentStep: isComplete(session)
            ? null
            : task.steps[session.currentStepIndex].title,
          done: isComplete(session),
        },
        effort: {
          elapsedMinutes: elapsedMin,
          attempts: session.attempts,
          hintsUsed: session.hintsUsed,
        },
        masteryNotes:
          session.masteryNotes.length > 0
            ? session.masteryNotes
            : ["No struggle spots recorded yet — keep going."],
        next: isComplete(session)
          ? "Done. Call teach_quiz to lock in understanding, then start a new task."
          : "Call teach_next_step to continue.",
      });
    }
  );

  // --- Teach Mode (any prompt) ---
  // teach_mode_on: load the Teach Mode system prompt + rules.
  server.tool(
    "teach_mode_on",
    "Turn on Teach Mode. Returns the Teach Mode system prompt + rules. After this, take the user's prompt as-is, break it into 3-7 steps, and call teach_plan — never write the user's code.",
    {},
    async () =>
      text({
        mode: "teach",
        systemPrompt: getTeachModePrompt(),
        rules: TEACH_MODE_RULES,
        howToUse: TEACH_MODE_HOW_TO_USE,
        examplePrompt: TEACH_MODE_EXAMPLE_PROMPT,
        next: "Break the user's prompt into 3-7 verifiable steps and call teach_plan with {prompt, steps, quiz}. Guide one step at a time after that.",
      })
  );

  // Shared teach_plan handler used by both teach_plan and teach_start_from_prompt.
  const teachPlanShape = {
    prompt: z.string().describe("The user's original prompt, as-is — e.g. 'Implement JWT auth'"),
    title: z.string().optional().describe("Optional short title for the plan"),
    steps: z
      .array(
        z
          .object({
            id: z.string().optional(),
            title: z.string().optional(),
            instruction: z.string().optional(),
            why: z.string().optional(),
            file: z.string().optional(),
            fileHint: z.string().optional(),
            whatToType: z.string().optional(),
            check: z.any().optional(),
            checkDescription: z.string().optional(),
            hintL1: z.string().optional(),
            hintL2: z.string().optional(),
            hintL3: z.string().optional(),
          })
          .passthrough()
      )
      .describe("3-7 steps, one action / one file / one concept each, each with instruction, why, file, hints, check"),
    quiz: z
      .array(
        z.object({
          question: z.string().optional(),
          options: z.array(z.string()).optional(),
          answerIndex: z.number().optional(),
          explanation: z.string().optional(),
        })
      )
      .optional()
      .describe("Optional 2-3 quiz questions. If omitted, Teachify supplies a default 2-question quiz."),
    mode: z.enum(["teach", "hint", "do"]).optional().default("teach"),
  };

  async function handleTeachPlan(args: {
    prompt?: string;
    title?: string;
    steps?: Array<Record<string, unknown>>;
    quiz?: Array<Record<string, unknown>>;
    mode?: "teach" | "hint" | "do";
  }) {
    const errors = validateTeachPlan({
      prompt: args.prompt,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      steps: (args.steps ?? []) as any,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      quiz: args.quiz as any,
      title: args.title,
    });
    if (errors.length > 0) {
      return text({
        error: "Teach plan rejected — fix the errors and call teach_plan again. No session was created.",
        errors,
        hint: "Steps must be 3-7, one action / one file / one concept each, each with non-empty title, instruction, why, file, hintL1, hintL2, hintL3, and a valid check. Quiz, if present, must be 2-3 questions.",
      });
    }
    const task = buildDynamicTask({
      prompt: args.prompt,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      steps: args.steps as any,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      quiz: args.quiz as any,
      title: args.title,
    });
    registerDynamicTask(task);
    const session = createSessionForTask(task, args.mode ?? "teach");
    return text({
      sessionId: session.id,
      taskId: task.id,
      mode: session.mode,
      prompt: args.prompt,
      task: {
        id: task.id,
        title: task.title,
        description: task.description,
        level: task.level,
        estimatedMinutes: task.estimatedMinutes,
        totalSteps: task.steps.length,
        learningOutcomes: task.learningOutcomes,
      },
      currentStep: toPublicStep(task, 0),
      rule: "The learner types every line. Teachify guides, verifies, hints, and quizzes — it never writes the solution. Step 1 only is returned here.",
      next: "Call teach_check_step with { sessionId, file, content } after the learner completes this step.",
    });
  }

  server.tool(
    "teach_plan",
    "Plan a Teach Mode session from ANY user prompt. Validates 3-7 steps (each with instruction, why, file, hints, check) and 2-3 quiz questions. On valid, creates a session and returns step 1 only — never the full solution. On invalid, returns clear errors and creates nothing.",
    teachPlanShape,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    async (args: any) => handleTeachPlan(args)
  );

  server.tool(
    "teach_start_from_prompt",
    "Alias of teach_plan for discoverability. Same schema, same behaviour: plan a Teach Mode session from ANY user prompt.",
    teachPlanShape,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    async (args: any) => handleTeachPlan(args)
  );

  // Convenience: list tasks without starting one (useful for clients).
  server.tool(
    "teach_list_tasks",
    "List available learning tasks (id, title, level, steps).",
    {},
    async () => text({ tasks: listTaskSummaries() })
  );

  return server;
}

async function main() {
  // Touch the loader early so a missing tasks dir fails fast with a clear error.
  loadTasks();
  const server = createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(`Teachify MCP server v${VERSION} running on stdio.`);
}

if (require.main === module) {
  main().catch((err) => {
    console.error("Teachify failed to start:", err);
    process.exit(1);
  });
}
