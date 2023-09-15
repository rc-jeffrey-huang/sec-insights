/* eslint-disable @typescript-eslint/ban-ts-comment */
/* eslint-disable @typescript-eslint/no-unsafe-call */
/* eslint-disable @typescript-eslint/no-unsafe-member-access */
/* eslint-disable @typescript-eslint/no-unsafe-assignment */
/* eslint-disable @typescript-eslint/restrict-template-expressions */
import { backendUrl } from "~/config";
import { BackendDocumentType, type BackendDocument } from "~/types/backend/document";
import { type SecDocument } from "~/types/document";
import { documentColors } from "~/utils/colors";

export const fromBackendDocumentToFrontend = (
  backendDocuments: BackendDocument[]
) => {
  const frontendDocs: SecDocument[] = [];
  backendDocuments.map((backendDoc, index) => {
    const frontendDocType = BackendDocumentType.TenK;

    // we have 10 colors for 10 documents
    const colorIndex = index < 10 ? index : 0;
    const payload = {
      id: backendDoc,
      url: `${backendUrl}api/download/${backendDoc}`,
      // @ts-ignore
      ticker: backendDoc.split(".")[0],
      // @ts-ignore
      fullName: backendDoc.split(".")[0],
      year: '',
      docType: frontendDocType,
      color: documentColors[colorIndex],
      quarter: "",
    } as unknown as SecDocument;
    frontendDocs.push(payload);
  });
  return frontendDocs;
};
