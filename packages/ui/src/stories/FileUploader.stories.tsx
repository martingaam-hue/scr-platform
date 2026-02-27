import type { Meta, StoryObj } from "@storybook/react";
import { FileUploader } from "../components/file-uploader";

const meta: Meta<typeof FileUploader> = {
  title: "Components/FileUploader",
  component: FileUploader,
};
export default meta;

export const Empty: StoryObj<typeof FileUploader> = {
  args: {
    accept: ".pdf,.doc,.docx,.xlsx",
    maxSizeMB: 25,
  },
};

export const WithFiles: StoryObj<typeof FileUploader> = {
  args: {
    files: [
      {
        file: new File([""], "business-plan-v3.pdf", { type: "application/pdf" }),
        progress: 100,
        status: "done",
      },
      {
        file: new File([""], "financial-model.xlsx", { type: "application/xlsx" }),
        progress: 65,
        status: "uploading",
      },
      {
        file: new File([""], "risk-assessment.pdf", { type: "application/pdf" }),
        progress: 0,
        status: "pending",
      },
    ],
  },
};
