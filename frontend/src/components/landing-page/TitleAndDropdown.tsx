import { useRouter } from "next/router";
import { useEffect, useState } from "react";

import { FiTrash2 } from "react-icons/fi";

import cx from "classnames";

import { AiOutlineArrowRight } from "react-icons/ai";
import { CgFileDocument } from "react-icons/cg";
import { useIntercom } from "react-use-intercom";
import { backendClient } from "~/api/backend";
import { LoadingSpinner } from "~/components/basics/Loading";
import FileUploader from '~/components/file-uploader';
import {
  MAX_NUMBER_OF_SELECTED_DOCUMENTS
} from "~/hooks/useDocumentSelector";
import useIsMobile from "~/hooks/utils/useIsMobile";
import s from './index.module.css';

export const TitleAndDropdown = () => {
  const router = useRouter();

  const { isMobile } = useIsMobile();

  const [isLoadingConversation, setIsLoadingConversation] = useState(false);
  const [fileList, setFiles] = useState<{fileID: string, file: File, progress: number}[]>([])

  const handleSubmit = (event: { preventDefault: () => void }) => {
    setIsLoadingConversation(true);
    event.preventDefault();
    const selectedDocumentIds = fileList.map((val) => val.file.name);
    backendClient
      .createConversation(selectedDocumentIds)
      .then((newConversationId) => {
        setIsLoadingConversation(false);
        router
          .push(`/conversation/${newConversationId}`)
          .catch(() => console.log("error navigating to conversation"));
      })
      .catch(() => console.log("error creating conversation "));
  };

  const handleRemoveDocument = (fileItem: {fileID: string, file: File, progress: number}) => {
    const targetIndex = fileList.findIndex((file) => file.fileID === fileItem.fileID)
    const copy_fileList = [...fileList]

    copy_fileList.splice(targetIndex, 1);
    setFiles(copy_fileList)
  }

  const isDocumentSelectionEnabled = fileList.length < MAX_NUMBER_OF_SELECTED_DOCUMENTS;

  const isStartConversationButtonEnabled = fileList.length > 0;


  const getFileSize = (size: number) => {
    if (size / 1024 < 10)
      return `${(size / 1024).toFixed(2)}KB`

    return `${(size / 1024 / 1024).toFixed(2)}MB`
  }

  const { boot } = useIntercom();

  useEffect(() => {
    boot();
  }, []);

  return (
    <div className="landing-page-gradient-1 relative flex h-max w-screen flex-col items-center font-lora ">
      <div className="mt-28 flex flex-col items-center">
        <div className="text-center text-4xl">
          Empower your organization&apos;s Business Intelligence
        </div>
      </div>
      {isMobile ? (
        <div className="mt-12 flex h-1/5 w-11/12 rounded border p-4 text-center">
          <div className="text-xl font-bold">
            To start analyzing documents, please switch to a larger screen!
          </div>
        </div>
      ) : (
        <div className="mt-5 flex h-min w-11/12 max-w-[1200px] flex-col items-center justify-center rounded-lg border-2 bg-white sm:h-[400px] md:w-9/12 ">
          <div className="p-4 text-center text-xl font-bold">
            Start your conversation by selecting the documents you want to
            explore
          </div>
          <FileUploader files={fileList} prepareFileList={setFiles} onFileListUpdate={setFiles}/>

          <div className="mt-2 flex h-full w-11/12 flex-col justify-start overflow-scroll px-4 ">
            {fileList.length === 0 && (
              <div className="m-4 flex h-full flex-col items-center justify-center bg-gray-00 font-nunito text-gray-90">
                <div>
                  <CgFileDocument size={46} />
                </div>
                <div className="w-84 text-center md:w-64">
                  Use the document selector above to start adding documents
                </div>
              </div>
            )}
            {fileList.map((file, index) => (
              <div
                key={index}
                className={cx(
                  index === 0 && "mt-2 border-t",
                  "group flex items-center justify-between border-b p-1 font-nunito font-bold text-[#868686] hover:bg-[#EAEAF7] hover:text-[#350F66] "
                )}
              >
                <div className="w-64 text-left">
                  <span className="font-bold">{file.file.name}</span>
                </div>
                <div className="w-24 text-left">{getFileSize(file.file.size)}</div>
                {file.progress < 100 && (
                  <div className={s.progressbar} style={{width: `${file.progress}%`}}/>
                )}
                {(file.progress < 100 && file.progress >= 0) && (
                  <div className={s.percent}>{`${file.progress}%`}</div>
                )}
                {file.progress === 100 && (
                  <button
                    className="mr-4 group-hover:text-[#FF0000]"
                    onClick={() => handleRemoveDocument(file)}
                  >
                    <FiTrash2 size={24} />
                  </button>
                )}
              </div>
            ))}
          </div>

          <div className="h-1/8 mt-2 flex w-full items-center justify-center rounded-lg bg-gray-00">
            <div className="flex flex-wrap items-center justify-center">
              {isDocumentSelectionEnabled && (
                <>
                  <div className="w-48 font-nunito md:ml-8 ">
                    Add up to{" "}
                    <span className="font-bold">
                      {" "}
                      {MAX_NUMBER_OF_SELECTED_DOCUMENTS -
                        fileList.length}
                    </span>{" "}
                    {isStartConversationButtonEnabled ? (
                      <>more docs</>
                    ) : (
                      <>docs</>
                    )}
                  </div>
                  <div className="ml-1 font-nunito ">
                    {isStartConversationButtonEnabled ? <>or</> : <>to</>}{" "}
                  </div>
                </>
              )}
              <div className="md:ml-12">
                <button
                  disabled={!isStartConversationButtonEnabled}
                  onClick={handleSubmit}
                  className={cx(
                    "m-4 rounded border bg-llama-indigo px-6 py-2 font-nunito text-white hover:bg-[#3B3775] disabled:bg-gray-30 ",
                    !isStartConversationButtonEnabled &&
                      "border-gray-300 bg-gray-300"
                  )}
                >
                  <div className="flex items-center justify-center">
                    {isLoadingConversation ? (
                      <div className="flex h-[22px] w-[180px] items-center justify-center">
                        <LoadingSpinner />
                      </div>
                    ) : (
                      <>
                        start your conversation
                        <div className="ml-2">
                          <AiOutlineArrowRight />
                        </div>
                      </>
                    )}
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
