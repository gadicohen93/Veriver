"use client";

import * as React from "react";
import { CaretSortIcon, CheckIcon } from "@radix-ui/react-icons";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
	Command,
	CommandEmpty,
	CommandGroup,
	CommandInput,
	CommandItem,
	CommandList,
} from "@/components/ui/command";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";

const frameworks = [
	{
		value: "Flagged Correctly. This is Misleading",
		label: "Flagged Correctly. This is Misleading",
	},
	{
		value: "This is an opinion not a fact",
		label: "This is an opinion not a fact",
	},
	{
		value: "This is Partially Correct",
		label: "This is Partially Correct",
	},
];

export function ComboboxDemo() {
	const [open, setOpen] = React.useState(false);
	const [value, setValue] = React.useState("");
	const [commentary, setCommentary] = React.useState("");

	return (
		<div className="flex flex-col">
			<Popover open={open} onOpenChange={setOpen}>
				<PopoverTrigger asChild>
					<Button
						variant="outline"
						role="combobox"
						aria-expanded={open}
						className="w-[450px] justify-between"
					>
						{value
							? frameworks.find(
									(framework) => framework.value === value
							  )?.label
							: "Select Feedback..."}
						<CaretSortIcon className="ml-2 h-4 w-4 shrink-0 opacity-50" />
					</Button>
				</PopoverTrigger>
				<PopoverContent className="w-[400px] p-0">
					<Command>
						{/* <CommandInput
							placeholder="Search framework..."
							className="h-9"
						/> */}
						<CommandList>
							<CommandEmpty>No framework found.</CommandEmpty>
							<CommandGroup>
								{frameworks.map((framework) => (
									<CommandItem
										key={framework.value}
										value={framework.value}
										onSelect={(currentValue) => {
											setValue(
												currentValue === value
													? ""
													: currentValue
											);
											setOpen(false);
										}}
									>
										{framework.label}
										<CheckIcon
											className={cn(
												"ml-auto h-4 w-4",
												value === framework.value
													? "opacity-100"
													: "opacity-0"
											)}
										/>
									</CommandItem>
								))}
							</CommandGroup>
						</CommandList>
					</Command>
				</PopoverContent>
			</Popover>
			{/* Commentary Section */}
			<textarea
				placeholder="Add your commentary for the agent here..."
				value={commentary}
				onChange={(e) => setCommentary(e.target.value)}
				className="mt-4 p-2 border border-gray-300 rounded-lg w-full"
				rows={4} // Adjust height as needed
			/>
		</div>
	);
}
